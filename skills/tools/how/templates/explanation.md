# Explanation template

Use this structure, adapted to what makes sense for the question. Not every section is needed for every question.

### Overview
1-2 paragraphs. What is this thing, what does it do, why does it exist. Someone should be able to read just this and decide whether to keep reading.

### Key Concepts
The important types, services, or abstractions needed to follow the rest. Brief definitions, not exhaustive.

### How It Works
The core of the explanation, and the longest section. Walk through the flow: what triggers it, what happens step by step, where data goes, what the decision points are.

Use prose, not pseudocode. Reference specific files and functions so the reader knows where to look, but don't dump large code blocks unless a snippet is essential to a point.

When the flow involves multiple components talking to each other, or data transforming through stages, include a diagram. Use mermaid (```mermaid) for structured flows (sequence diagrams, flowcharts, component graphs) or ASCII art for simpler relationships where mermaid would be overkill. If prose covers the flow, skip the diagram.

### Where Things Live
A brief file/directory map. Just the ones someone would need to start working here.

### Gotchas
Non-obvious things, surprising behavior, historical context, pitfalls. Skip this section if there's nothing worth calling out.
