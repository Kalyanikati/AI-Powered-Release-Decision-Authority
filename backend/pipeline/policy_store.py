import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

_POLICY_DOCS = [
    ("pol_001", "All production deployments require a security scan completed within 72 hours before release."),
    ("pol_002", "Any change to production environment must have a documented rollback plan approved by the team lead."),
    ("pol_003", "Database schema changes require a rollback migration script and must be reviewed by the DBA team."),
    ("pol_004", "Changes impacting PII data must have compliance team sign-off and a security scan before deployment."),
    ("pol_005", "Critical urgency hotfixes to production must undergo a post-release review within 24 hours."),
    ("pol_006", "All releases must include test evidence with at least 60% unit test coverage before deployment."),
    ("pol_007", "Hotfix deployments bypass the standard release window but require tech lead approval and an incident ticket."),
    ("pol_008", "Security scans are mandatory for any service touching authentication, authorization, or data encryption."),
    ("pol_009", "All release requests must specify a monitoring plan including tools such as Kibana or Grafana and monitoring duration."),
    ("pol_010", "Releases impacting external APIs must notify consumer teams at least 2 hours before deployment."),
    ("pol_011", "Any deployment involving financial or payment data requires dual approval from security and compliance teams."),
    ("pol_012", "Production database changes without a tested rollback script are blocked by default governance policy."),
]

_collection = None


def _get_collection():
    global _collection
    if _collection is not None:
        return _collection

    client = chromadb.EphemeralClient()
    ef = DefaultEmbeddingFunction()
    _collection = client.get_or_create_collection(
        name="sdlc_policies",
        embedding_function=ef,
    )

    if _collection.count() == 0:
        _collection.add(
            documents=[doc[1] for doc in _POLICY_DOCS],
            ids=[doc[0] for doc in _POLICY_DOCS],
        )

    return _collection


def retrieve_relevant_policies(query: str, n_results: int = 3) -> list:
    collection = _get_collection()
    results = collection.query(query_texts=[query], n_results=n_results)
    policies = []
    for i, doc in enumerate(results["documents"][0]):
        policies.append({
            "id": results["ids"][0][i],
            "policy": doc,
            "relevance_score": round(1 - results["distances"][0][i], 3),
        })
    return policies