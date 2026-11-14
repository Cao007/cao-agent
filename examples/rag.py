"""最小内存 RAG：官方 splitter、embeddings 与 vector store，不依赖外部向量库。"""

import asyncio

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.app.ai.model import create_model
from backend.app.core.config import Settings


async def main():
    settings = Settings()
    model = create_model(settings)
    if model is None:
        raise SystemExit("RAG 示例需要 MODEL_MODE=openai 与 embedding 模型权限")
    documents = [
        Document(
            page_content="退货政策：签收后七天内可以申请退货。",
            metadata={"source": "售后政策", "id": "returns"},
        ),
        Document(
            page_content="配送政策：普通商品付款后两个工作日内发货。",
            metadata={"source": "配送政策", "id": "shipping"},
        ),
    ]
    chunks = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=20).split_documents(
        documents
    )
    store = InMemoryVectorStore(
        OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=settings.openai_api_key.get_secret_value(),
            base_url=settings.openai_base_url,
        )
    )
    await store.aadd_documents(chunks)
    retriever = store.as_retriever(search_kwargs={"k": 2})
    question = "收货后多久可以退货？"
    sources = await retriever.ainvoke(question)
    context = "\n".join(f"[{i}] {doc.page_content}" for i, doc in enumerate(sources, 1))
    answer = await model.ainvoke(
        [
            SystemMessage(content="只根据检索材料回答，用 [编号] 引用；缺少依据时说明。"),
            HumanMessage(content=f"材料：\n{context}\n问题：{question}"),
        ]
    )
    print(
        {
            "answer": answer.text,
            "citations": [{"number": i, **doc.metadata} for i, doc in enumerate(sources, 1)],
        }
    )


if __name__ == "__main__":
    asyncio.run(main())
