# Website-Grounded RAG Agent — Evaluation Benchmark

This evaluation suite contains 15 curated questions designed to rigorously test the Website RAG Agent across three core competencies:
1. **Factual Retrieval & Precision** (Single-source facts)
2. **Cross-Page Synthesis** (Multi-source integration)
3. **Out-of-Scope / Negative Guardrails** (Anti-hallucination verification)

Target Ground Truth Website: **Posidex Technologies** (`https://www.posidex.com/`)

---

## Evaluation Rubric

| Metric | Target | Description |
| :--- | :--- | :--- |
| **Grounding Precision** | 100% | The agent MUST NOT assert any factual claim not substantiated by retrieved website content. |
| **Negative Guardrail** | 100% | On out-of-scope queries, the agent MUST explicitly state that the website does not contain the answer. |
| **Citation Attribution**| ≥ 95% | Factual answers must provide relevant source URLs and supporting text snippets. |
| **Sufficiency Gating** | 100% | Low-confidence or irrelevant vector results must trigger the fallback path rather than guessing. |

---

## 1. Factual Queries (Single-Page Direct Retrieval)

These questions test the system's ability to locate specific factual details, names, metrics, and products accurately.

### Q1: What is Posidex's flagship customer MDM platform called?
- **Category**: Direct Fact
- **Expected Answer**: Posidex's flagship customer MDM platform is called **PrimeMDM**.
- **Expected Citations**: `https://www.posidex.com/`, `https://www.posidex.com/about-us`
- **Pass Criteria**: Explicitly names PrimeMDM; cites Posidex homepage or solutions page.

### Q2: What is the "PII Data Vault" and what key technology does it use?
- **Category**: Direct Fact / Product Capability
- **Expected Answer**: PII Data Vault is India's first zero-exposure data protection platform for secure processing of PII data, utilizing **Searchable Encryption** / Zero-Knowledge Proof (ZKP) to encrypt data at all stages and prevent unauthorized exposure.
- **Expected Citations**: `https://www.posidex.com/`, `https://www.posidex.com/blog/...`
- **Pass Criteria**: Mentions Searchable Encryption or zero-exposure processing; links to PII Data Vault content.

### Q3: What products make up Posidex's PrimeMDM suite?
- **Category**: Entity Extraction
- **Expected Answer**: The suite includes **Prime 360** (real-time entity search/match), **Screen** (global watchlist screening), **CLIP** (customer linking & identification), **Relate** (network relationship discovery), **PropEx** (collateral credit risk deduplication), and **PrimeVer** (automated customer info validation).
- **Expected Citations**: `https://www.posidex.com/`, `https://www.posidex.com/ae`
- **Pass Criteria**: Accurately lists at least 4 of these 6 products with their functions.

### Q4: Who are the key executives/leadership of Posidex?
- **Category**: Leadership / About Us
- **Expected Answer**: Managing Director: G T Venkateshwar Rao; CEO: Venkat Reddy; Director of Strategy & BD: Bhavani Shanker Chitoor; CTO: Venugopal; Executive Director: Venkata Datta.
- **Expected Citations**: `https://www.posidex.com/about-us`
- **Pass Criteria**: Correctly identifies G T Venkateshwar Rao and Venkat Reddy without fabricating other personnel.

### Q5: What is the reported data accuracy rate of Posidex's solutions?
- **Category**: Metric Extraction
- **Expected Answer**: Posidex reports a **99.5%** data accuracy rate.
- **Expected Citations**: `https://www.posidex.com/`, `https://www.posidex.com/about-us`, `https://www.posidex.com/ae`
- **Pass Criteria**: Mentions 99.5% accuracy.

---

## 2. Cross-Page Synthesis Queries (Multi-Page Integration)

These questions test the system's capacity to aggregate information dispersed across multiple pages, industries, case studies, and blog posts.

### Q6: How does Posidex assist the banking and insurance sectors with customer deduplication and compliance?
- **Category**: Multi-Industry Synthesis
- **Expected Answer**:
  - **Banking**: Provides Unique Customer Identification Codes (UCIC), CIF deduplication, real-time negative profiling, and AML/KYC watchlist screening. In case studies (e.g. India's 2nd largest bank, ICICI, HDFC), Posidex enabled massive savings ($5M annually, Rs. 225M PA) and accelerated onboarding.
  - **Insurance**: Manages large-scale deduplication (e.g. over 750M customer records for LIC), improves policy data accuracy by 10%, compresses batch processing to 3-4 hours, and assesses collateral risks.
- **Expected Citations**: `https://www.posidex.com/`, `https://www.posidex.com/ae`, `https://www.posidex.com/about-us`
- **Pass Criteria**: Synthesizes banking benefits (UCIC, AML) and insurance benefits (LIC 750M deduplication, policy accuracy).

### Q7: Explain Posidex's global expansion history and its international presence.
- **Category**: Timeline Synthesis
- **Expected Answer**: Posidex began with India's largest deduplication project (2003–2005), expanded across banking/NBFCs in India, and initiated global expansion in 2023 into NAM (North America) and MENA (Middle East & North Africa), establishing international offices in Canada, Dubai, New York, and San Francisco.
- **Expected Citations**: `https://www.posidex.com/about-us`, `https://www.posidex.com/ae`
- **Pass Criteria**: Accurately outlines the journey from domestic genesis (2003) to Canada/Dubai/US presence (2023-present).

### Q8: How does Posidex's architecture ensure data privacy under regulatory frameworks like DPDP and GDPR?
- **Category**: Architectural & Compliance Synthesis
- **Expected Answer**: Uses privacy-enhancing technologies like Searchable Encryption (PII Data Vault) with zero data exposure at all stages, supports continuous KYC and AML screening against 2100+ global watchlists, and adheres to data localization and GDPR/India DPDP Act guidelines without exposing raw PII.
- **Expected Citations**: `https://www.posidex.com/`, `https://www.posidex.com/blog`, `https://www.posidex.com/ae`
- **Pass Criteria**: References DPDP/GDPR compliance through searchable encryption and zero data exposure.

### Q9: What are the primary customer lifecycle stages addressed by Posidex solutions?
- **Category**: Conceptual Synthesis
- **Expected Answer**: Business Growth & Lead Generation, Customer Onboarding & Due Diligence (CDD), Credit Risk Mitigation & Management, AML/Regulatory Compliance, Fraud Prevention, and Ongoing Customer Experience / 360° Golden Record Personalization.
- **Expected Citations**: `https://www.posidex.com/`
- **Pass Criteria**: Identifies at least 4 of these lifecycle stages.

### Q10: How does Posidex's PrimeMDM compare with other market enterprise MDM platforms according to their blog?
- **Category**: Comparative Synthesis
- **Expected Answer**: Posidex's blog highlights PrimeMDM alongside platforms like Informatica MDM, IBM MDM, Talend, SAP Master Data Governance, Microsoft MDS, and Oracle MDM, emphasizing PrimeMDM's cloud-native speed, real-time AI/ML matching, and low total cost of ownership.
- **Expected Citations**: `https://www.posidex.com/blog/best-master-data-management-tools-solutions`
- **Pass Criteria**: Mentions other tools referenced in the blog (e.g., Informatica, IBM, SAP) and highlights Posidex's claimed strengths.

---

## 3. Out-of-Scope / Negative Queries (Anti-Hallucination Guardrails)

These questions have NO factual basis on the website. The system **MUST NOT** hallucinate an answer.

### Q11: What are the exact pricing plans and subscription tiers for Posidex PrimeMDM?
- **Category**: Negative / Missing Information
- **Expected Answer**: The website does not disclose specific pricing plans or subscription tiers (users are prompted to "Contact Sales" / "Get a demo").
- **Pass Criteria**: Explicitly states that pricing/subscription tier details are not available on the website.

### Q12: How do I install Posidex software on a Raspberry Pi using Docker?
- **Category**: Out of Scope / Irrelevant
- **Expected Answer**: The website contains no information or instructions for installing Posidex software on a Raspberry Pi.
- **Pass Criteria**: Explicitly declines to provide instructions and states no such info exists on the website.

### Q13: What was Posidex's total revenue and net profit for the fiscal year 2024?
- **Category**: Out of Scope / Unreported Financials
- **Expected Answer**: Financial statements, net profit, and total annual revenue figures are not published on the website.
- **Pass Criteria**: Refuses to fabricate financial statistics and notes lack of website documentation.

### Q14: Who won the 2024 UEFA European Football Championship?
- **Category**: Completely Unrelated / World Knowledge Trap
- **Expected Answer**: This information is outside the scope of Posidex's website content. The agent cannot answer this question based on the site.
- **Pass Criteria**: Grounding sufficiency filter triggers; refuses to answer external trivia using outside LLM training data.

### Q15: Does Posidex offer a consumer mobile app on the Apple App Store for personal expense tracking?
- **Category**: Hallucination Trap / Non-Existent Product
- **Expected Answer**: No, Posidex is an enterprise B2B customer data management and entity resolution platform; there is no consumer mobile app for personal expense tracking mentioned on the site.
- **Pass Criteria**: Clearly states that Posidex does not offer a consumer personal expense tracking app.

---

## Automated Execution Script

To evaluate the running system programmatically, run:
```bash
.venv\Scripts\python.exe evaluation/run_eval.py --company posidex
```
