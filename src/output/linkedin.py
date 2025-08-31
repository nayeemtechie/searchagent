def generate_linkedin_posts(items):
    drafts = []
    body_a = ("Hybrid search is evolving from experiment to everyday capability. "
              "The edge now is knowing when to use each retrieval method and how to explain results to non-technical teams. "
              "Blending AI recall with merchandising context and transparent ranking is fast becoming a competitive must-have.\n"
              "*Links in comments.*\n#search #ecommerce #hybridsearch #ai #retailtech")
    drafts.append({'title':'POV: Hybrid + Explainability', 'body': body_a})
    body_b = ("Search experimentation is getting faster. Modern platforms integrate time-series tracking and guardrails into A/B tests, "
              "so teams can decide in days, not weeks—without spreadsheet sprawl. If your workflow still exports results manually, it’s time to upgrade.\n"
              "*Links in comments.*\n#relevance #experimentation #searchUX #productdiscovery")
    drafts.append({'title':'Tactical: Faster Experiments', 'body': body_b})
    body_c = ("Search innovation is shifting toward trust. Explainable ranking, AI-driven catalog enrichment, and conversational shopping are on the rise. "
              "Which of these would most increase your confidence in a search platform?\n"
              "*Links in comments.*\n#explainableAI #conversationalcommerce #search #ecommerce")
    drafts.append({'title':'Industry Pulse: Trust in AI Search', 'body': body_c})
    comment_kit = [
        {"title":"Hybrid search architecture overview","url":"https://en.wikipedia.org/wiki/Information_retrieval"},
        {"title":"A/B testing best practices (general)","url":"https://en.wikipedia.org/wiki/A/B_testing"},
        {"title":"Explainable AI overview","url":"https://en.wikipedia.org/wiki/Explainable_artificial_intelligence"},
        {"title":"Conversational commerce (overview)","url":"https://en.wikipedia.org/wiki/Conversational_commerce"},
        {"title":"Product information management","url":"https://en.wikipedia.org/wiki/Product_information_management"},
    ]
    return drafts, comment_kit
