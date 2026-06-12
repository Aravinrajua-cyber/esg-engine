# Word Report Visual QA Checklist

Use this checklist after regenerating the report:

```bat
cd /d C:\Hackathon\esg-engine
.\.venv\Scripts\python.exe -m src.report.build_report
```

## Required Manual Checks

- [ ] Open `outputs\report\ESG_Momentum_Engine_Final_Report.docx` in Microsoft Word.
- [ ] Update all fields, including the table of contents.
- [ ] Confirm the title page clearly says synthetic demonstration / not investment advice.
- [ ] Confirm each figure is readable at normal zoom.
- [ ] Confirm figure captions remain attached to the corresponding figure.
- [ ] Confirm no figure is cut off by page margins.
- [ ] Confirm no table exceeds page margins.
- [ ] Confirm page breaks do not split headings from first paragraphs.
- [ ] Confirm bibliography/reference formatting is consistent.
- [ ] Export to PDF and inspect the PDF separately.

## Status In This Session

Not passed. This Codex session did not open Microsoft Word or inspect an exported PDF.
