# Evaluation results

Generated 2026-10-29 by `python eval/run_eval.py --answers`.

## Setup

- Embedding model: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- Chunk size 500 characters, overlap 100; the app sends the top 5 chunks to the LLM
- 26 questions with a known answer page, over 3 fictional sample documents (22 chunks in total):

| Document | Language | Pages | Chunks |
|---|---|---|---|
| acme_employee_handbook.pdf | English | 5 | 10 |
| nova_hizmet_sozlesmesi.pdf | Turkish | 4 | 7 |
| solaris_x2_user_manual.pdf | English | 3 | 5 |

## Retrieval: is the correct page in the top-k chunks?

| Question set | n | Hit@1 | Hit@3 | Hit@5 | MRR |
|---|---|---|---|---|---|
| **All questions** | 26 | 81% | 92% | 96% | 0.85 |
| Same language as document | 21 | 90% | 100% | 100% | 0.94 |
| Cross-language (TR question, EN doc or vice versa) | 5 | 40% | 60% | 80% | 0.51 |
| English questions | 15 | 93% | 100% | 100% | 0.96 |
| Turkish questions | 11 | 64% | 82% | 91% | 0.72 |

## Per question

| # | Question | Expected | Rank | Top result |
|---|---|---|---|---|
| 1 | When was Acme Analytics founded? | acme_employee_handbook.pdf p. 1 | 1 | acme_employee_handbook.pdf p. 1 (0.77) |
| 2 | Who should I contact with questions about a policy? | acme_employee_handbook.pdf p. 1 | 1 | acme_employee_handbook.pdf p. 1 (0.31) |
| 3 | What are the core working hours? | acme_employee_handbook.pdf p. 2 | 1 | acme_employee_handbook.pdf p. 2 (0.72) |
| 4 | How many days a week can I work from home? | acme_employee_handbook.pdf p. 2 | 1 | acme_employee_handbook.pdf p. 2 (0.57) |
| 5 | Can I carry over unused holiday to next year? | acme_employee_handbook.pdf p. 3 | 3 | acme_employee_handbook.pdf p. 5 (0.38) |
| 6 | By what time must I tell my manager that I am sick? | acme_employee_handbook.pdf p. 3 | 1 | acme_employee_handbook.pdf p. 3 (0.48) |
| 7 | What is the daily meal allowance when travelling? | acme_employee_handbook.pdf p. 4 | 1 | acme_employee_handbook.pdf p. 4 (0.74) |
| 8 | How long do I have to return my laptop after leaving? | acme_employee_handbook.pdf p. 5 | 1 | acme_employee_handbook.pdf p. 5 (0.47) |
| 9 | How long must a password be? | acme_employee_handbook.pdf p. 5 | 1 | acme_employee_handbook.pdf p. 5 (0.60) |
| 10 | Nova Yazılım'ın merkezi nerede? | nova_hizmet_sozlesmesi.pdf p. 1 | 1 | nova_hizmet_sozlesmesi.pdf p. 1 (0.67) |
| 11 | Sözleşme ne kadar süre geçerli? | nova_hizmet_sozlesmesi.pdf p. 1 | 1 | nova_hizmet_sozlesmesi.pdf p. 1 (0.67) |
| 12 | Aylık hizmet ücreti ne kadar? | nova_hizmet_sozlesmesi.pdf p. 2 | 1 | nova_hizmet_sozlesmesi.pdf p. 2 (0.60) |
| 13 | Fatura kaç gün içinde ödenmeli? | nova_hizmet_sozlesmesi.pdf p. 2 | 1 | nova_hizmet_sozlesmesi.pdf p. 2 (0.68) |
| 14 | Gecikme faizi oranı nedir? | nova_hizmet_sozlesmesi.pdf p. 2 | 1 | nova_hizmet_sozlesmesi.pdf p. 2 (0.64) |
| 15 | Teknik destek hangi saatlerde verilir? | nova_hizmet_sozlesmesi.pdf p. 3 | 1 | nova_hizmet_sozlesmesi.pdf p. 3 (0.67) |
| 16 | Planlı bakım ne zaman yapılır? | nova_hizmet_sozlesmesi.pdf p. 3 | 1 | nova_hizmet_sozlesmesi.pdf p. 3 (0.43) |
| 17 | Sözleşmeyi feshetmek için kaç gün önceden bildirim gerekir? | nova_hizmet_sozlesmesi.pdf p. 4 | 3 | nova_hizmet_sozlesmesi.pdf p. 1 (0.59) |
| 18 | How long does it take to fully charge the speaker? | solaris_x2_user_manual.pdf p. 1 | 1 | solaris_x2_user_manual.pdf p. 1 (0.60) |
| 19 | Is a wall charger included in the box? | solaris_x2_user_manual.pdf p. 1 | 1 | solaris_x2_user_manual.pdf p. 1 (0.54) |
| 20 | How many hours does the battery last? | solaris_x2_user_manual.pdf p. 2 | 1 | solaris_x2_user_manual.pdf p. 2 (0.66) |
| 21 | How do I reset the speaker to factory settings? | solaris_x2_user_manual.pdf p. 3 | 1 | solaris_x2_user_manual.pdf p. 3 (0.50) |
| 22 | Yılda kaç gün ücretli izin hakkım var? (cross) | acme_employee_handbook.pdf p. 3 | 3 | nova_hizmet_sozlesmesi.pdf p. 2 (0.55) |
| 23 | Masrafları kaç gün içinde göndermeliyim? (cross) | acme_employee_handbook.pdf p. 4 | 5 | nova_hizmet_sozlesmesi.pdf p. 2 (0.63) |
| 24 | Hoparlörün garanti süresi ne kadar? (cross) | solaris_x2_user_manual.pdf p. 3 | **miss** | nova_hizmet_sozlesmesi.pdf p. 4 (0.53) |
| 25 | How long is customer data kept after the contract ends? (cross) | nova_hizmet_sozlesmesi.pdf p. 4 | 1 | nova_hizmet_sozlesmesi.pdf p. 4 (0.65) |
| 26 | What uptime does the service provider guarantee? (cross) | nova_hizmet_sozlesmesi.pdf p. 3 | 1 | nova_hizmet_sozlesmesi.pdf p. 3 (0.65) |

## Example answers

LLM: `groq` (`openai/gpt-oss-20b`). Answered in the question's language: 7/7.

**Q:** How many days a week can I work from home?

**A:** You can work from home up to two days per week. [acme_employee_handbook.pdf, p. 2]

*Sources:* acme_employee_handbook.pdf p. 2

**Q:** Fatura kaç gün içinde ödenmeli ve gecikme faizi nedir?

**A:** Fatura 10 gün içinde ödenmeli ve gecikme faizi aylık %2’dir. [ nova_hizmet_sozlesmesi.pdf, p. 2]

*Sources:* nova_hizmet_sozlesmesi.pdf p. 2

**Q:** Yılda kaç gün ücretli izin hakkım var?

**A:** Yılda 25 gün ücretli yıllık izin hakkınız var. [acme_employee_handbook.pdf, p. 3]

*Sources:* acme_employee_handbook.pdf p. 3

**Q:** How long is customer data kept after the contract ends?

**A:** Customer data is retained for 60 days after the contract ends, after which it is permanently deleted. [nova_hizmet_sozlesmesi.pdf, p. 4]

*Sources:* nova_hizmet_sozlesmesi.pdf p. 4

**Q:** What uptime does the service provider guarantee?

**A:** The service provider guarantees that the system will be available at least 99.5 % of the time each month. [nova_hizmet_sozlesmesi.pdf, p. 3]

*Sources:* nova_hizmet_sozlesmesi.pdf p. 3

**Q:** Hoparlör kaç saat çalışır?

**A:** Yüklenen belgelerde bu sorunun cevabını bulamadım.

*Sources:* none

**Q:** What is the name of Acme's CEO?

**A:** I couldn't find the answer in the uploaded documents.

*Sources:* none


## How to read these numbers

- **Hit@k** is the share of questions where a chunk from the correct page is among the k most similar chunks. Hit@5 matters most here, because the app gives the LLM 5 chunks: if the right page is in them, the LLM can answer.
- **MRR** (mean reciprocal rank) also rewards ranking the right page higher: 1.0 means always first.
- This is a small test set (26 questions, 22 chunks). With so few chunks, picking 5 at random would already find the right page about 23-41% of the time (pages have 1-2 chunks), so treat these as a sanity check, not a benchmark. One question changes a score by about 4 points.
- It measures **retrieval only**. Whether the final answer is correct is shown in the example answers, but not scored.
