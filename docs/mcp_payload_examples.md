# Research Intelligence MCP
# Tool Payload Examples

This document contains realistic payload examples for testing the MCP server using:

- MCP Inspector
- Claude Desktop
- ChatGPT MCP
- Future API clients

---

# 1. search_papers

Search academic literature across Semantic Scholar and arXiv.

---

## Example 1
## General AI Research Search

```json
{
  "query": "agentic retrieval augmented generation",
  "providers": [
    "semantic_scholar",
    "arxiv"
  ],
  "limit": 10,
  "offset": 0,
  "sort": "relevance"
}
```

---

## Example 2
## Recent RAG Papers

```json
{
  "query": "retrieval augmented generation",
  "providers": [
    "semantic_scholar",
    "arxiv"
  ],
  "limit": 20,
  "offset": 0,
  "year_from": 2023,
  "sort": "publication_date"
}
```

---

## Example 3
## LLM Evaluation Papers

```json
{
  "query": "large language model evaluation",
  "providers": [
    "semantic_scholar"
  ],
  "limit": 15,
  "offset": 0,
  "year_from": 2022,
  "fields_of_study": [
    "Computer Science"
  ],
  "sort": "citation_count"
}
```

---

## Example 4
## Open Access Only

```json
{
  "query": "multimodal agents",
  "providers": [
    "semantic_scholar",
    "arxiv"
  ],
  "limit": 10,
  "offset": 0,
  "open_access_only": true
}
```

---

## Example 5
## Search by Paper Title

```json
{
  "query": "Attention Is All You Need",
  "providers": [
    "semantic_scholar",
    "arxiv"
  ],
  "limit": 5
}
```

---

## Example 6
## Search by Author

```json
{
  "query": "Yann LeCun",
  "providers": [
    "semantic_scholar"
  ],
  "limit": 10
}
```

---

## Example 7
## Search by arXiv Category

```json
{
  "query": "vision language models",
  "providers": [
    "arxiv"
  ],
  "limit": 10,
  "fields_of_study": [
    "cs.CV",
    "cs.AI"
  ]
}
```

---

# Real Queries For Testing

```json
{
  "query": "LLM agents"
}
```

```json
{
  "query": "Model Context Protocol"
}
```

```json
{
  "query": "GraphRAG"
}
```

```json
{
  "query": "long context language models"
}
```

```json
{
  "query": "deep research agents"
}
```

---

# 2. get_paper

Retrieve metadata for one paper.

---

# arXiv Examples

---

## Example 1
## Attention Is All You Need

```json
{
  "provider": "arxiv",
  "paper_id": "1706.03762"
}
```
or 

```json
{
  "provider": "arxiv",
  "paper_id": "https://arxiv.org/abs/1706.03762"
}
```

Paper:

https://arxiv.org/abs/1706.03762

---

## Example 2
## DeepSeek-R1

```json
{
  "provider": "arxiv",
  "paper_id": "2501.12948"
}
```

---

## Example 3
## GraphRAG

```json
{
  "provider": "arxiv",
  "paper_id": "2404.16130"
}
```

---

## Example 4
## MCP Paper

```json
{
  "provider": "arxiv",
  "paper_id": "2504.12389"
}
```

(if available)

---

## Example 5
## Full URL Input

Your normalizer should also accept:

```json
{
  "provider": "arxiv",
  "paper_id": "https://arxiv.org/abs/1706.03762v7"
}
```

---

# Semantic Scholar Examples

Semantic Scholar supports multiple identifier types.

---

## Example 1
## DOI

```json
{
  "provider": "semantic_scholar",
  "paper_id": "10.48550/arXiv.1706.03762"
}
```

---

## Example 2
## DOI URL

```json
{
  "provider": "semantic_scholar",
  "paper_id": "https://doi.org/10.48550/arXiv.1706.03762"
}
```

---

## Example 3
## Semantic Scholar Paper ID

```json
{
  "provider": "semantic_scholar",
  "paper_id": "204e3073870fae3d05bcbc2f6a8e263d9b72e776"
}
```

---

## Example 4
## Corpus ID

```json
{
  "provider": "semantic_scholar",
  "paper_id": "CorpusID:52967399"
}
```

---

# Recommended MCP Inspector Payloads

---

## Search Test

```json
{
  "query": "agentic retrieval augmented generation",
  "providers": [
    "semantic_scholar",
    "arxiv"
  ],
  "limit": 10,
  "year_from": 2023
}
```

---

## Get Paper Test

```json
{
  "provider": "arxiv",
  "paper_id": "1706.03762"
}
```

---

# Future Tools Payload Examples

---

# 3. get_paper_citations

```json
{
  "provider": "semantic_scholar",
  "paper_id": "10.48550/arXiv.1706.03762",
  "limit": 20,
  "offset": 0
}
```

---

# 4. get_paper_references

```json
{
  "provider": "semantic_scholar",
  "paper_id": "10.48550/arXiv.1706.03762",
  "limit": 20,
  "offset": 0
}
```

---

# 5. get_related_papers

```json
{
  "provider": "semantic_scholar",
  "paper_id": "10.48550/arXiv.1706.03762",
  "limit": 10
}
```

---

# 6. resolve_paper_access

```json
{
  "provider": "semantic_scholar",
  "paper_id": "10.48550/arXiv.1706.03762"
}
```

Expected output:

```json
{
  "status": "open_access",
  "landing_page_url": "...",
  "pdf_url": "...",
  "repository": "arxiv"
}
```

---

# End-to-End Workflow Examples

---

## Workflow 1

```text
search_papers
      ↓
get_paper
      ↓
get_paper_references
      ↓
get_related_papers
```

---

## Workflow 2

```text
search_papers
      ↓
get_paper
      ↓
get_paper_citations
```

---

## Workflow 3

```text
search_papers
      ↓
get_paper
      ↓
resolve_paper_access
      ↓
download pdf
```