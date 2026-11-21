# Recording script (about 7 minutes)

For a screen recording at 1440×900 or 1920×1080, browser zoom 110–125%. Start the server with `python -m demo`, open http://127.0.0.1:8000, press **Reset**, tick **Hinglish captions** if you want the on-screen subtitle line. Lines in *italics* are suggested voice-over; the English line is for subtitles.

| Time | Click | Voice-over (Hinglish) | English subtitle |
|---|---|---|---|
| 0:00 | (title screen) | *"AI agent aapke liye loan disburse kare, UPI payment kare. Par bank kaise jaane ki agent asli hai, aur apni limit mein hai?"* | An AI agent can disburse a loan or pay over UPI. How does the bank know it is genuine and within its limits? |
| 0:25 | — | *"Singapore ka MAS isko 'Know Your Agent' keh raha hai. Aaj hum India ke liye ek working version dekhenge."* | MAS calls this Know Your Agent. Today we look at a working version for India. |
| 0:45 | **Onboard four agents** | *"Har agent ka ek signed manifest hai: kaun hai, kiske liye kaam karta hai, kya authority hai, mandate kya hai, aur kitna bharosa."* | Each agent has a signed manifest: identity, whom it represents, authority, mandate and assurance. |
| 1:30 | **Credit bureau check** | *"Consent loan underwriting ke liye hai, to bureau report pull ho sakti hai. Teeno gates green."* | Consent covers loan underwriting, so the bureau pull is allowed. All three gates pass. |
| 2:00 | **Loan disbursal ₹1,50,000** | *"Sanctioned amount, borrower ka verified account. Auto-execute, aur rail ko evidence hash ke saath request gayi."* | Sanctioned amount to the verified account. Auto-executed, with the evidence hash sent to the rail. |
| 2:30 | **UPI groceries ₹1,249** | *"Reserve Pay jaisa ₹10,000 ka block, sirf approved dukaanein."* | A Reserve Pay-style ₹10,000 block, approved merchants only. |
| 2:50 | **Large disbursal ₹3,50,000** | *"Mandate ke andar hai, par ₹2 lakh se upar. Isliye insaan approve karega: Escalate."* | Within the mandate but above ₹2 lakh, so a human approves it: Escalate. |
| 3:20 | **Prompt-injected payee** | *"Ab asli khel. Borrower ki salary slip PDF mein chhupa instruction: ₹4,80,000 doosre VPA par bhejo. Agent bhatak gaya."* | Now the attack. A salary-slip PDF hides an instruction to send ₹4,80,000 to another VPA. The agent falls for it. |
| 3:50 | (point at RK-006, RK-007, MD-008) | *"Gate ne teen cheezein pakdi: payee allowlist mein nahi, amount instruction se match nahi, aur payee untrusted PDF se aaya. DENY."* | The gates catch three things: payee not allowlisted, amount does not match the instruction, payee came from an untrusted PDF. Denied. |
| 4:30 | **Forged agent credential** | *"Nakli agent, nakli issuer. Signature kisi trusted key se match nahi hua. Aage check karne ki zarurat hi nahi."* | A fake agent from a fake issuer. The signature matches no trusted key, so evaluation stops there. |
| 5:00 | **Bureau data for marketing** | *"Consent loan ke liye tha, marketing ke liye nahi. DPDP purpose limitation, seedha DENY."* | Consent was for the loan, not marketing. DPDP purpose limitation: denied. |
| 5:30 | **Replay last envelope** | *"Hacker ne wahi signed request dobara bheji. Replay pakda gaya."* | An attacker resends the same signed request. Replay caught. |
| 5:50 | **Tamper with the log**, then **Verify chain** | *"Koi insider log mein DENY ko AUTO-EXECUTE kar de? Hash chain toot jaata hai, aur pata chal jaata hai kaunsa record badla."* | What if an insider edits a DENY in the log? The hash chain breaks and shows which record changed. |
| 6:30 | (README on GitHub) | *"Code open source hai, link description mein. Ye personal project hai, adapters mock hain."* | The code is open source; link in the description. Personal project, adapters are mocks. |

Tips: hide the bookmarks bar, use a clean browser profile, and pause a beat on each verdict banner so viewers can read the rule ids.
