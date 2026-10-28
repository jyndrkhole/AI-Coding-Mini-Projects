# Specialists

The runtime is an in-process orchestrator. It does not call a hosted model unless one is deliberately added later, because the brief has to run with no API key and the tests must not spend money.

Each specialist has a fixed instruction, a short list of tools, and a structured result.

- ScoreAnalystAgent copies NPS, counts, intervals, and the small-sample list from tools.
- VoiceOfCustomerAgent ranks themes from tool output and quotes only comments the example tool returned. A rise in detractor comments while NPS fell is described as an association, not a cause.
- ChurnRiskAgent copies revenue exposed and expected revenue at risk and states that the churn rates are assumptions.
- ActionPlannerAgent ranks fixes and callbacks after the first three specialists finish. It can recommend a call. It cannot place one.
- ReportWriterAgent assembles the brief. FactCheck then compares claims, quotes, themes, and callback ids with the bundle.

If a specialist raises, the others are kept and that section of the brief is marked unavailable.

The OpenAI Agents SDK is not imported. Its current APIs need a live model client, which this build does not require. The tool names, phase order, and fact check match the brief’s agent design.
