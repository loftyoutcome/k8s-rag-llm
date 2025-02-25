import logging
import re

from openai import BadRequestError
from typing import Any, Dict, List

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)


def format_context(results: List[Dict[str, Any]]) -> str:
    """Format search results into context for the LLM"""
    context_parts = []

    for result in results:
        # TODO: make metadata keys configurable
        ticket_metadata = result.metadata
        ticket_content = result.page_content

        context_parts.append(
            f"Key: {ticket_metadata['ticket']} | Status: {ticket_metadata['status']} - "
            f"Type: {ticket_metadata['type']}\n"
            f"Content: {ticket_content}...\n"
        )

    return "\n\n".join(context_parts)


def trim_answer(generated_answer: str, label_separator: str) -> str:
    """
    From the generated_answer, remove all content after and including
    the provided label separator
    Args:
        generated_answer (str): the generated answer to remove from
        label_separator (str): string after which content needs to be trimmed
                               Note: this string will also be trimmed
    Returns:
        str: Cleaned answer with all content before the label separator
    """
    if not generated_answer:  # Handle empty text
        return ""
    answer = generated_answer
    # Split text at the token and take only the content before it
    if label_separator in generated_answer:
        answer = generated_answer.split(label_separator, 1)[0]
        logging.info(
            f"Label separator: {label_separator} seems to have been included in the generated answer and it has been removed: {answer}")

    return answer.strip()


def get_answer_with_settings(question, retriever, client, model_id, max_tokens, model_temperature, system_prompt):
    docs = retriever.invoke(input=question)
    logging.info(f"Number of relevant documents retrieved and that will be used as context for query: {len(docs)}")

    logging.info(f"Relevant docs retrieved from Vector store: {docs}")
    context = format_context(docs)
    logging.info(f"Length of context after formatting: {len(context)}")
    logging.info(f"Context after formatting: {context}")

    logging.info("Calling chat completions for JSON model...")
    try:
        completions = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Context:\n{context}\n\nQuestion: {question}",
                },
            ],
            max_tokens=max_tokens,
            temperature=model_temperature,
            stream=False,
        )
    except BadRequestError as e:
        if (e.status_code == 400 and
                "Please reduce the length of the messages or completion." in e.body.get("message", "") and
                len(docs) > 1
        ):
            docs = docs[:-1]  # removing last document
            context = format_context(docs)
            logging.info(f"Need to decrease context - length of context after formatting: {len(context)}")
            try:
                completions = client.chat.completions.create(
                    model=model_id,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": f"Context:\n{context}\n\nQuestion: {question}",
                        },
                    ],
                    max_tokens=max_tokens,
                    temperature=model_temperature,
                    stream=False,
                )
            except Exception as e:
                # Handle any error
                logging.error(f"An unexpected error occurred: {e}")
                errorToUI = {
                    "answer": f"Please try another question. Received error from LLM invocation: {e}",
                    "relevant_tickets": [],
                    "sources": [],
                    "context": context,
                }
                return errorToUI

    except Exception as e:
        # Handle any error
        logging.error(f"An unexpected error occurred: {e}")
        errorToUI = {
            "answer": f"Please try another question. Received error from LLM invocation: {e}",
            "relevant_tickets": [],
            "sources": [],
            "context": context,
        }
        return errorToUI

    generated_answer = completions.choices[0].message.content

    # Handle common hallucinations observed:
    #    1. Added-Context hallucination
    #    2. Added-Question hallucination
    #    3. Added-Context hallucination just labelled as "Content" (instead of Context like 1)
    logging.info(f"Removing any observed hallucinations in the generated answer: {generated_answer}")
    labels_to_trim = ["<|im_end|>", "Context:", "Question:", "Content:"]
    answer = generated_answer

    for label in labels_to_trim:
        if label in answer:
            answer = trim_answer(answer, label)

    answer = answer.replace("<|im_start|>", "")

    logging.info(f"Answer (after cleanup): {answer}")

    answerToUI = {
        "answer": answer,
        "relevant_tickets": [r.metadata["ticket"] for r in docs],
        "sources": [r.metadata["source"] for r in docs],
        "context": context,  # TODO: if this is big consider logging context here and sending some reference id to UI
    }
    return answerToUI


def get_answer_with_settings_with_weaviate_filter(question, vectorstore, client, model_id, max_tokens, model_temperature, system_prompt, relevant_docs):
    # from typing import List
    #
    # from langchain_core.documents import Document
    # from langchain_core.runnables import chain

    # @chain
    # def retriever(query: str) -> List[Document]:
    #     docs, scores = zip(*vectorstore.similarity_search_with_score(query, k=relevant_docs, alpha=1))
    #     for doc, score in zip(docs, scores):
    #         print("----> ", score)
    #         doc.metadata["score"] = score
    #
    #     return docs

    search_kwargs = {
        "k": relevant_docs,
        "alpha": 0.5,
    }

    ticket_id = extract_zendesk_ticket_id(query=question)

    if ticket_id:
        from weaviate.collections.classes.filters import Filter

        logging.info(f"Using ticket id {ticket_id} filter")
        # Use Weaviate’s `Filter` class to build the filter
        search_kwargs["filters"] = Filter.by_property("ticket").equal(ticket_id)

    retriever = vectorstore.as_retriever(
        # search_type="mmr",
        search_kwargs=search_kwargs,
    )
    logging.info("Created Vector DB retriever successfully. \n")

    return get_answer_with_settings(question, retriever, client, model_id, max_tokens, model_temperature, system_prompt)


def extract_zendesk_ticket_id(query):
    # TODO: implement smth smarter

    # Check if the word "ticket" exists in the query (case insensitive)
    if not re.search(r'\bticket\b', query, re.IGNORECASE):
        return None  # Return None if "ticket" is not present

    # Extract numeric ticket ID (assumes tickets are six digit numbers)
    match = re.search(r'\b\d{6,}\b', query)
    return match.group(0) if match else None
