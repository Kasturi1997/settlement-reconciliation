# GitHub Upload Guide

Use these steps after extracting the project folder.

## Option 1: Upload From GitHub Website

1. Create a new GitHub repository.
2. Name it `settlement-reconciliation-exception-agent`.
3. Keep it public if you want recruiters to view it easily.
4. Upload all files from this project folder.
5. Open `README.md` on GitHub and confirm the project overview is visible.
6. Share the repository URL with recruiters.

## Option 2: Upload From Terminal

Run these commands from inside the project folder:

```bash
git init
git add .
git commit -m "Add settlement reconciliation exception agent"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/settlement-reconciliation-exception-agent.git
git push -u origin main
```

Replace `YOUR-USERNAME` with your GitHub username.

## Suggested Recruiter Message

Hi, I am sharing a self-initiated fintech analytics project where I built a
synthetic settlement reconciliation workflow. It calculates expected merchant
settlements from order, payment, refund, fee, GST, chargeback, settlement, and
payout data, identifies mismatches, and generates investigation memos for
operations review.

Project link: paste your GitHub link here

