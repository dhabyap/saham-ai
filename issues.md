## Analisa Saham Enhancement: Shareholder Ownership (>1%)

This document outlines tasks for enhancing the "Analisa Saham" application, specifically focusing on shareholder ownership data greater than 1%.

### Task 1: Implement Force-Directed Graph Visualization for Shareholder Ownership

**Objective:** Visualize relationships between stocks, brokers, and shareholders with >1% ownership using a force-directed graph.

**Description:**
The current system stores shareholder ownership data. We need to display this data in an interactive force-directed graph, similar to what `vis-network` offers. This visualization should clearly show which entities (brokers, institutional shareholders) own more than 1% of which stocks, and the connections between them.

**Acceptance Criteria:**
-   A new page/section in the application displays the force-directed graph.
-   Nodes in the graph should represent:
    -   Stocks (e.g., BBCA, TLKM)
    -   Brokers (e.g., XC, PD, CC)
    -   Major Shareholders (entities holding >1% of a stock, not individual retail accounts).
-   Edges should represent ownership relationships.
-   Edges should be styled to indicate the percentage of ownership (e.g., thicker lines for higher percentages, color coding).
-   The graph must be interactive: users can drag nodes, zoom, and click on nodes/edges to view basic information (e.g., stock name, broker code, ownership percentage).
-   Data for the graph should be sourced from the existing database tables containing shareholder ownership information (ensure only >1% holdings are included).

**Technical Notes:**
-   Research `vis-network` or similar JavaScript library for graph visualization.
-   API endpoint needed to supply graph data (nodes and edges) to the frontend.
-   Frontend integration (Vue.js if applicable, or plain HTML/JS).

### Task 2: Track and Display Historical Ownership Changes

**Objective:** Enable tracking and visualization of historical changes in shareholder ownership percentage for specific stocks.

**Description:**
Users need to understand accumulation or distribution trends over time. This involves storing historical snapshots of ownership data and presenting it in a time-series format.

**Acceptance Criteria:**
-   Modify the database schema to store historical ownership percentages and dates (if not already supported).
-   When viewing a specific stock, a new section/tab displays a chart (e.g., line chart) showing the ownership percentage evolution of key shareholders (>1% ownership) over time.
-   Users can select a time range for the historical view.
-   For each major shareholder (>1%), show their entry and exit points or significant changes in percentage.

**Technical Notes:**
-   Identify appropriate database changes (e.g., new table `stock_ownership_history` or additions to existing tables).
-   Backend logic to query and aggregate historical data.
-   Frontend integration for rendering time-series charts (e.g., Chart.js, ApexCharts, or similar).

---
**Guidance for Junior Programmer:**
-   Start with Task 1 (Visualization) as it's more self-contained.
-   Break down each task into smaller sub-tasks (e.g., "design DB schema for history", "create API endpoint for graph data", "implement frontend component for graph").
-   Use existing code patterns and adhere to project's coding standards.
-   Ask questions if any part of the task is unclear.

### Task 3: Enhance Shareholder Ownership Data Interaction and Analysis

**Objective:** Improve the usability and analytical capabilities of the >1% shareholder ownership data through filtering, exporting, custom alerts, aggregation, and benchmarking.

**Description:**
Building upon the existing shareholder ownership data, this task aims to provide more powerful tools for users to interact with and derive insights from the data.

**Acceptance Criteria:**
-   **Filtering/Sorting:** Implement dynamic filtering and sorting options for the >1% ownership data. Users should be able to:
    -   Filter by ownership percentage range.
    -   Filter by specific brokers or shareholder types (e.g., retail, institutional, foreign).
    -   Filter by date ranges for historical data.
    -   Sort data by percentage (ascending/descending), shareholder name, stock ticker, or date.
-   **Export Data:** Provide a function to export the currently displayed >1% ownership data into common formats.
    -   Export to CSV.
    -   Export to Excel (XLSX).
-   **Custom Notification/Alerts:** Allow users to set up personalized alerts for significant changes in >1% ownership.
    -   Users can define thresholds (e.g., "if ownership of BBCA by broker XC changes by +/- 0.5%").
    -   Notifications via Telegram.
-   **Sector/Industry Aggregation:** Implement a view that aggregates >1% ownership data at the sector or industry level.
    -   Users can see total percentage held by major shareholders within a chosen sector/industry.
    -   Identify sectors with high institutional interest.
-   **Benchmarking:** Provide tools to compare >1% ownership trends between similar stocks or against market indices.
    -   Compare ownership structure of two selected stocks.
    -   Visualize how a stock's major ownership changes relative to a sector index.

**Technical Notes:**
-   For filtering/sorting, consider frontend-driven solutions for responsiveness, backed by efficient database queries.
-   Export functionality will require server-side processing to generate the files.
-   Alerting will likely involve cron jobs or background tasks to monitor changes and trigger notifications.
-   Sector/Industry data might require integration with a stock master data service or manual mapping.
-   Benchmarking will require robust data retrieval and comparison logic.