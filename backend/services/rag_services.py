def query(case_id: int, message: str, jurisdiction: str):
    

    return {
        "answer": (
            "This is a temporary RAG response. "
            "The real retrieval and language-model pipeline "
            "will be connected here."
        ),

        "jurisdiction": jurisdiction,

        "confidence": 0.50,

        "citations": [],

        "warnings": [
            
            "The response has not been verified by an expert."
        ],

        "classification": "Ayurveda",

        "needs_expert_review": True
    }