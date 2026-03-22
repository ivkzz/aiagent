"""RAG Retriever — ядро системы поиска по документам.

Предоставляет высокоуровневый API для поиска:
- Одиночный поиск
- Multi-query расширение через LLM
- Дедупликация и агрегация результатов
- Обработка ошибок и логирование

Архитектура:
    RAGRetriever
    ├── _single_search()        # базовый поиск через Chroma
    ├── _generate_queries()     # генерация альтернативных запросов через LLM
    ├── _merge_results()        # объединение и дедупликация из нескольких запросов
    └── search()                # публичный API
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel

from app.core.logger import get_logger
from app.rag.config import RAGConfig, get_rag_config
from app.rag.utils import (
    aggregate_documents_content,
    deduplicate_documents,
    format_search_results,
)
from app.rag.vectorstore import similarity_search

log = get_logger(__name__)


@dataclass
class RAGSearchResult:
    """Структурированный результат поиска RAG.

    Поля:
        content: агрегированный текст фрагментов
        sources: список названий документов-источников
        total_found: общее количество найденных документов до ограничения k
    """

    content: str
    sources: list[str]
    total_found: int = 0


class RAGRetriever:
    """Ретривер для поиска по векторной базе с multi-query поддержкой."""

    def __init__(
        self,
        llm: BaseChatModel | None = None,
        config: RAGConfig | None = None,
    ) -> None:
        """Инициализирует ретривер.

        Args:
            llm: Языковая модель для генерации альтернативных запросов.
                 Если None, multi-query отключён.
            config: Конфигурация RAG (использует глобальную если None)
        """
        self.llm = llm
        self.config = config or get_rag_config()

    async def _generate_queries(self, original_query: str) -> list[str]:
        """Генерирует альтернативные поисковые запросы через LLM.

        Args:
            original_query: Исходный запрос пользователя

        Returns:
            Список альтернативных запросов (включая оригинальный)
        """
        if not self.llm or not self.config.multi_query_enabled:
            return [original_query]

        prompt = f"""\
        Ты — эксперт по поиску информации. Given исходный запрос, сгенерируй {self.config.multi_query_max_queries} альтернативных формулировок этого запроса для поиска по документам.

        Цель: покрыть разные аспекты и формулировки, чтобы найти максимально релевантные документы.
        Запросы должны быть:
        - Краткими и конкретными
        - Использовать синонимы
        - Перефразировать, но сохранять смысл
        - Не менять суть запроса

        Оригинальный запрос: {original_query}

        Верни ТОЛЬКО список запросов, по одному на строку. Без нумерации, без пояснений.
        """

        try:
            response = await self.llm.ainvoke(
                [{"role": "user", "content": prompt}],
                config={"temperature": self.config.multi_query_llm_temperature},
            )
            content = str(response.content).strip()

            # Парсим строки
            queries = [line.strip() for line in content.split("\n") if line.strip()]

            # Ограничиваем количество
            queries = queries[: self.config.multi_query_max_queries]

            # Всегда включаем оригинальный запрос первым
            if original_query not in queries:
                queries.insert(0, original_query)

            # Убираем дубликаты запросов (но сохраняем порядок)
            seen: set[str] = set()
            unique_queries = []
            for q in queries:
                q_norm = q.lower().strip()
                if q_norm and q_norm not in seen:
                    seen.add(q_norm)
                    unique_queries.append(q)

            if len(unique_queries) > 1:
                log.info(
                    f"Multi-query: оригинальный → {len(unique_queries)} вариантов:\n"
                    + "\n".join([f"  • {q}" for q in unique_queries])
                )
            else:
                log.info("Multi-query: только оригинальный запрос (LLM не сгенерировал варианты)")

            return unique_queries[: self.config.multi_query_max_queries]

        except Exception as exc:
            log.warning(f"Ошибка генерации multi-query запросов: {exc}. Используется оригинальный.")
            return [original_query]

    async def _single_search(
        self,
        query: str,
        k: int,
        score_threshold: float | None = None,
    ) -> list[Document]:
        """Выполняет одиночный поиск в векторной базе.

        Args:
            query: Поисковый запрос
            k: Количество результатов
            score_threshold: Минимальный порог релевантности

        Returns:
            Список документов с score в metadata
        """
        if score_threshold is None:
            score_threshold = 0.0  # Отключаем жесткий фильтр по умолчанию, чтобы не терять релевантные документы

        try:
            docs = await asyncio.to_thread(
                similarity_search,
                query=query,
                score_threshold=score_threshold,
                k=min(k, self.config.max_k),
            )

            log.debug(f"Поиск '{query[:50]}...': найдено {len(docs)} документов")
            return docs

        except Exception as exc:
            log.error(f"Ошибка поиска для запроса '{query[:50]}...': {exc}")
            return []

    async def search(
        self,
        query: str,
        k: int | None = None,
        *,
        score_threshold: float | None = None,
        use_multi_query: bool = False,  # Отключено для ускорения работы агента
        deduplicate: bool = True,
        aggregate: bool = True,
        return_content_only: bool = False,
    ) -> str:
        """Поиск по документам с опциональным multi-query и агрегацией.

        Args:
            query: Поисковый запрос пользователя
            k: Количество результатов (по умолчанию из конфига)
            score_threshold: Порог релевантности (по умолчанию из конфига)
            use_multi_query: Использовать LLM для генерации альтернативных запросов
            deduplicate: Удалять дубликаты
            aggregate: Агрегировать результаты в единый текст
            return_content_only: Если True, возвращает только текст без форматирования

        Returns:
            Форматированный результат поиска или агрегированный текст
        """
        if k is None:
            k = self.config.default_k
        if score_threshold is None:
            score_threshold = self.config.score_threshold

        start_time = asyncio.get_event_loop().time()
        log.info(f"RAG search: '{query}' (k={k}, dedup={deduplicate}, multi={use_multi_query})")

        try:
            # 1. Генерируем список запросов
            queries: list[str] = []
            if use_multi_query and self.llm:
                queries = await self._generate_queries(query)
                if len(queries) > 1:
                    log.debug(f"Multi-query сгенерировал {len(queries)} запросов")
            else:
                queries = [query]

            # 2. Выполняем параллельный поиск по всем запросам
            search_tasks = [
                self._single_search(q, k, score_threshold) for q in queries
            ]
            all_results: list[list[Document]] = await asyncio.gather(*search_tasks, return_exceptions=False)

            # 3. Объединяем все результаты
            merged_docs: list[Document] = []
            total_found = 0
            for i, docs in enumerate(all_results):
                if i > 0:  # Логируем только если multi-query был использован
                    log.debug(f"  Запрос '{queries[i]}...': найдено {len(docs)} документов")
                merged_docs.extend(docs)
                total_found += len(docs)

            if not merged_docs:
                log.info(f"По запросу '{query}...' ничего не найдено")
                return "Ничего релевантного не найдено. Попробуйте уточнить запрос."

            # 4. Дедупликация
            if deduplicate:
                before_dedup = len(merged_docs)
                final_docs = deduplicate_documents(merged_docs, self.config)
                after_dedup = len(final_docs)
                final_docs = final_docs[:k]
                log.debug(
                    f"Дедупликация: {before_dedup} → {after_dedup} "
                    f"(дубликатов удалено: {before_dedup - after_dedup})"
                )
            else:
                final_docs = merged_docs[:k]

            log.info(
                f"Поиск завершён: запросов={len(queries)}, "
                f"всего найдено={total_found}, возвращаю={len(final_docs)}"
            )

            # 5. Агрегация или форматирование
            if aggregate:
                if return_content_only:
                    return aggregate_documents_content(final_docs, max_length=self.config.max_aggregated_length)
                else:
                    return format_search_results(final_docs, self.config, max_docs=k)
            else:
                return format_search_results(final_docs, self.config, max_docs=k, include_scores=True)

        except Exception as exc:
            log.exception(f"Критическая ошибка RAG поиска: {exc}")
            return f"Ошибка при поиске: {str(exc)}. Попробуйте переформулировать запрос."
        finally:
            elapsed = asyncio.get_event_loop().time() - start_time
            log.debug(f"Общее время поиска: {elapsed:.2f}s")

    async def search_with_sources(
        self,
        query: str,
        k: int | None = None,
        *,
        score_threshold: float | None = None,
        use_multi_query: bool = False,  # Отключено для ускорения работы агента
        deduplicate: bool = True,
    ) -> "RAGSearchResult":
        """Поиск с возвратом структурированного результата (content + sources).

        Args:
            query: Поисковый запрос
            k: Количество результатов
            score_threshold: Порог релевантности
            use_multi_query: Использовать multi-query
            deduplicate: Дедуплицировать

        Returns:
            RAGSearchResult с aggregated content и списком источников
        """
        if k is None:
            k = self.config.default_k
        if score_threshold is None:
            score_threshold = self.config.score_threshold

        start_time = asyncio.get_event_loop().time()
        log.info(f"RAG search_with_sources: '{query}' (k={k})")

        try:
            # Используем существующую логику поиска
            queries: list[str] = []
            if use_multi_query and self.llm:
                queries = await self._generate_queries(query)
                if len(queries) > 1:
                    log.debug(f"Multi-query: {len(queries)} запросов")
            else:
                queries = [query]

            search_tasks = [
                self._single_search(q, k, score_threshold) for q in queries
            ]
            all_results = await asyncio.gather(*search_tasks, return_exceptions=False)

            merged_docs: list[Document] = []
            total_found = 0
            for docs in all_results:
                merged_docs.extend(docs)
                total_found += len(docs)

            if not merged_docs:
                return RAGSearchResult(
                    content="Ничего релевантного не найдено. Попробуйте уточнить запрос.",
                    sources=[],
                    total_found=0,
                )

            if deduplicate:
                final_docs = deduplicate_documents(merged_docs, self.config)[:k]
            else:
                final_docs = merged_docs[:k]

            # Извлекаем источники (уникальные имена файлов)
            sources_set: set[str] = set()
            for doc in final_docs:
                source = doc.metadata.get(self.config.FIELD_SOURCE)
                if source:
                    sources_set.add(source)

            # Агрегируем контент (без форматирования источников, они отдельно)
            content = aggregate_documents_content(
                final_docs, max_length=self.config.max_aggregated_length
            )

            elapsed = asyncio.get_event_loop().time() - start_time
            log.debug(f"Поиск с источниками завершён за {elapsed:.2f}s: {len(final_docs)} док., {len(sources_set)} источн.")

            return RAGSearchResult(
                content=content,
                sources=sorted(sources_set),
                total_found=total_found,
            )

        except Exception as exc:
            log.exception(f"Ошибка search_with_sources: {exc}")
            return RAGSearchResult(
                content=f"Ошибка при поиске: {str(exc)}. Попробуйте переформулировать запрос.",
                sources=[],
                total_found=0,
            )