# Three-Minute Demonstration Script

## 0:00-0:25 - The Problem

Traditional ESG ratings are often hard to explain and slow to change. A company can improve its behaviour before the rating catches up, or look highly rated while its recent momentum is weakening. The ESG Momentum Engine is designed to make that difference visible.

## 0:25-0:45 - Level Versus Momentum

The system separates ESG level from ESG momentum. Level answers: "How strong does the company look now?" Momentum answers: "Is it improving or deteriorating?" Showing both helps a user avoid treating a static high score and a fast-improving company as the same thing.

## 0:45-1:10 - Screening 500 Companies

The leaderboard is the main screening surface. The user can search across up to 500 companies, filter by market, sector, grade, classification, and risk flags, then sort by rank, score, company, coverage, or classification.

## 1:10-1:35 - How The Leaderboard Works

Each row shows the company, score, grade, confidence band, classification, data coverage, and comparison control. The score is not a single mystery number: the user can open the weight sandbox and see how rankings change when pillar weights change.

## 1:35-2:00 - Opening One Company

Clicking a company opens the detail view. This shows the score, confidence band, pillar breakdown, classification map, any available timeseries, data coverage, and risk flags. The goal is to explain why the company is ranked where it is, not just display a rank.

## 2:00-2:25 - Components Explained

The current model groups evidence into understandable components: sentiment dynamics, transition readiness, governance credibility, disclosure behaviour, data coverage, risk flags, and confidence. In a live integration, these would map to auditable ESG, non-ESG, financial, disclosure, news, and market-data inputs.

## 2:25-2:40 - Why The Data Is Synthetic

This demo is visibly labelled synthetic because the 500-company dataset is generated for demonstration and testing. The label prevents judges or users from mistaking the prototype for live investment research.

## 2:40-2:55 - Replacing Demo Data

In production, validated CSV files or authorised API feeds would replace the synthetic JSON. The same schema, validation checks, missing-data rules, and confidence labels would remain, but the values would come from licensed sources and approved calculations.

## 2:55-3:00 - What We Can And Cannot Claim

What we can claim: the prototype demonstrates an explainable workflow for screening ESG momentum and reviewing risk. What we cannot claim: that the synthetic rankings identify real winners, predict returns, or constitute investment advice.

