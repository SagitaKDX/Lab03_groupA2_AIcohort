// Frontend Controller - ReAct Agent Web Playground

document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const llmProvider = document.getElementById("llm-provider");
    const modelName = document.getElementById("model-name");
    const maxSteps = document.getElementById("max-steps");
    const stepsVal = document.getElementById("steps-val");
    const promptTemplate = document.getElementById("prompt-template");
    const systemPrompt = document.getElementById("system-prompt");
    const settingsForm = document.getElementById("settings-form");
    let promptTemplates = {};
    let savedPromptTemplate = "prompt_with_fewshot";
    
    const chatMessages = document.getElementById("chat-messages");
    const chatInput = document.getElementById("chat-input");
    const chatSendBtn = document.getElementById("chat-send-btn");
    const agentThinking = document.getElementById("agent-thinking");
    
    const statLatency = document.getElementById("stat-latency");
    const statTokens = document.getElementById("stat-tokens");
    const statCost = document.getElementById("stat-cost");
    const statSteps = document.getElementById("stat-steps");

    // Dynamic slider label
    maxSteps.addEventListener("input", (e) => {
        stepsVal.textContent = e.target.value;
    });

    function loadSelectedPromptTemplate() {
        const selectedTemplate = promptTemplates[promptTemplate.value];
        if (selectedTemplate === undefined) {
            systemPrompt.value = "";
            showNotification("Prompt templates were not loaded from prompt.py. Restart the backend server.");
            return;
        }
        systemPrompt.value = selectedTemplate;
    }

    promptTemplate.addEventListener("change", () => {
        loadSelectedPromptTemplate();
    });

    // Toggle LLM Provider defaults and local configurations panel display
    llmProvider.addEventListener("change", (e) => {
        const localGroup = document.getElementById("local-settings-group");
        if (e.target.value === "openai") {
            modelName.value = "gpt-4o";
            localGroup.classList.add("hidden");
        } else if (e.target.value === "google") {
            modelName.value = "gemini-2.5-flash";
            localGroup.classList.add("hidden");
        } else if (e.target.value === "local") {
            modelName.value = "Phi-3-mini-4k-instruct-q4.gguf";
            localGroup.classList.remove("hidden");
        }
    });

    // 1. Fetch current settings on load
    async function loadSettings() {
        try {
            const res = await fetch("/api/settings");
            if (res.ok) {
                const data = await res.json();
                llmProvider.value = data.provider || "openai";
                modelName.value = data.model || "gpt-4o";
                maxSteps.value = data.max_steps || 10;
                stepsVal.textContent = maxSteps.value;
                promptTemplates = {};
                if (Array.isArray(data.prompt_templates)) {
                    promptTemplate.innerHTML = "";
                    data.prompt_templates.forEach(template => {
                        promptTemplates[template.key] = template.content;

                        const option = document.createElement("option");
                        option.value = template.key;
                        option.textContent = template.label;
                        promptTemplate.appendChild(option);
                    });
                } else {
                    showNotification("Backend did not return prompt templates from prompt.py. Restart server.py.");
                }
                savedPromptTemplate = data.prompt_template || "prompt_with_fewshot";
                promptTemplate.value = savedPromptTemplate;
                systemPrompt.value = data.system_prompt ?? "";
                if (!systemPrompt.value && savedPromptTemplate !== "no_prompt") {
                    loadSelectedPromptTemplate();
                }
                
                // Toggle local model panel visibility
                const localGroup = document.getElementById("local-settings-group");
                if (data.provider === "local") {
                    localGroup.classList.remove("hidden");
                } else {
                    localGroup.classList.add("hidden");
                }
                
                // Populate local variables
                document.getElementById("local-model-path").value = data.local_model_path || "Phi-3-mini-4k-instruct-q4.gguf";
                document.getElementById("local-n-ctx").value = data.local_n_ctx || 4096;
                document.getElementById("local-n-threads").value = data.local_n_threads || "";
                document.getElementById("local-stop").value = data.local_stop || "<|end|>,Observation:";
                
                // Set checkboxes
                const tools = data.tools || [];
                const checkboxes = document.querySelectorAll('input[name="tools"]');
                checkboxes.forEach(cb => {
                    cb.checked = tools.includes(cb.value);
                });
            }
        } catch (err) {
            console.error("Failed to load settings:", err);
            showNotification("Error loading settings from backend.");
        }
    }

    // 2. Save settings form handler
    settingsForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        
        // Gather checked tools
        const selectedTools = [];
        const checkboxes = document.querySelectorAll('input[name="tools"]:checked');
        checkboxes.forEach(cb => {
            selectedTools.push(cb.value);
        });

        const config = {
            provider: llmProvider.value,
            model: modelName.value,
            max_steps: parseInt(maxSteps.value, 10),
            tools: selectedTools,
            prompt_template: promptTemplate.value,
            system_prompt: promptTemplate.value !== savedPromptTemplate
                ? (promptTemplates[promptTemplate.value] ?? systemPrompt.value)
                : systemPrompt.value,
            local_model_path: document.getElementById("local-model-path").value,
            local_n_ctx: parseInt(document.getElementById("local-n-ctx").value, 10) || 4096,
            local_n_threads: document.getElementById("local-n-threads").value ? parseInt(document.getElementById("local-n-threads").value, 10) : null,
            local_stop: document.getElementById("local-stop").value
        };

        try {
            const res = await fetch("/api/settings", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(config)
            });
            const data = await res.json().catch(() => ({}));
            if (res.ok) {
                savedPromptTemplate = data.settings?.prompt_template || config.prompt_template;
                systemPrompt.value = data.settings?.system_prompt ?? config.system_prompt;
                showNotification("Agent customization applied successfully!");
            } else {
                showNotification(data.message ? `Failed to save settings: ${data.message}` : "Failed to save settings.");
            }
        } catch (err) {
            console.error("Save settings error:", err);
            showNotification("Failed to connect to backend server.");
        }
    });

    // 3. Send query to agent handler
    async function handleSend() {
        const query = chatInput.value.trim();
        if (!query) return;

        // Clear input and display User message bubble
        chatInput.value = "";
        appendMessage(query, "user");
        
        // Show thinking indicator & scroll to bottom
        agentThinking.classList.remove("hidden");
        scrollToBottom();

        try {
            const res = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query })
            });

            if (res.ok) {
                const data = await res.json();
                
                // Hide thinking indicator
                agentThinking.classList.add("hidden");
                
                // Render Agent Response
                appendAgentMessage(data.answer, data.trace);
                
                // Update Telemetry stats
                updateTelemetry(data.telemetry);
                
                // Render raw log event stream
                renderRawLogs(data.raw_events);
            } else {
                const errText = await res.text();
                agentThinking.classList.add("hidden");
                appendMessage(`Error: ${errText}`, "system");
            }
        } catch (err) {
            console.error("Chat request failed:", err);
            agentThinking.classList.add("hidden");
            appendMessage("Failed to communicate with the agent backend. Please check connection.", "system");
        }
    }

    chatSendBtn.addEventListener("click", handleSend);
    chatInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") handleSend();
    });

    // UI Helper: Append Simple Message
    function appendMessage(text, sender) {
        const msgDiv = document.createElement("div");
        msgDiv.className = `message ${sender}`;
        
        let avatarIcon = "fa-user";
        if (sender === "system") avatarIcon = "fa-triangle-exclamation";
        
        msgDiv.innerHTML = `
            <div class="message-content">
                <i class="fa-solid ${avatarIcon} message-avatar"></i>
                <div class="text-block">
                    <p>${escapeHTML(text)}</p>
                </div>
            </div>
        `;
        chatMessages.appendChild(msgDiv);
        scrollToBottom();
    }

    // UI Helper: Append Agent Response with Accordion Trace
    function appendAgentMessage(answer, trace) {
        const msgDiv = document.createElement("div");
        msgDiv.className = "message agent";
        
        // Parse simple markdown-like elements (tables, bullet points, bolds)
        const formattedAnswer = parseSimpleMarkdown(answer);
        
        let traceHTML = "";
        if (trace && trace.length > 0) {
            traceHTML = `
                <div class="trace-container">
                    <div class="trace-title" onclick="toggleTraceVisibility(this)">
                        <i class="fa-solid fa-chevron-down"></i> Reasoning Trace (${trace.length} Steps)
                    </div>
                    <div class="trace-steps">
                        ${trace.map((step, idx) => `
                            <div class="trace-step">
                                <div class="trace-step-header" onclick="toggleStepContent(this)">
                                    <span><i class="fa-solid fa-brain"></i> Step ${step.step} - Thought & Action</span>
                                    <i class="fa-solid fa-chevron-down"></i>
                                </div>
                                <div class="trace-step-content">
                                    <div class="thought-box">
                                        <strong>Thought:</strong><br>${escapeHTML(step.thought)}
                                    </div>
                                    ${step.action ? `
                                        <div class="action-box">
                                            <strong>Action:</strong> ${escapeHTML(step.action)}
                                        </div>
                                    ` : ""}
                                    ${step.observation ? `
                                        <div class="observation-box">
                                            <strong>Observation:</strong><br>${escapeHTML(step.observation)}
                                        </div>
                                    ` : ""}
                                </div>
                            </div>
                        `).join("")}
                    </div>
                </div>
            `;
        }

        msgDiv.innerHTML = `
            <div class="message-content" style="flex-direction: column;">
                <div style="display: flex; gap: 16px; width: 100%;">
                    <i class="fa-solid fa-robot message-avatar"></i>
                    <div class="text-block" style="flex-grow: 1;">
                        ${formattedAnswer}
                    </div>
                </div>
                ${traceHTML}
            </div>
        `;
        
        chatMessages.appendChild(msgDiv);
        scrollToBottom();
    }

    // UI Helper: Update Telemetry Dashboard Stats
    function updateTelemetry(tel) {
        if (!tel) return;
        statLatency.textContent = tel.latency_ms !== null ? `${tel.latency_ms} ms` : "-- ms";
        statTokens.textContent = tel.tokens !== null ? tel.tokens.toLocaleString() : "--";
        statCost.textContent = tel.cost !== null ? `$${tel.cost.toFixed(4)}` : "$0.000";
        statSteps.textContent = tel.steps !== null ? tel.steps : "--";
    }

    // UI Helper: Show Toast Notification Banner
    function showNotification(message) {
        const notif = document.createElement("div");
        notif.className = "notification";
        notif.textContent = message;
        document.body.appendChild(notif);
        
        setTimeout(() => {
            notif.style.opacity = "0";
            setTimeout(() => notif.remove(), 300);
        }, 3000);
    }

    // UI Helper: Smooth scroll to bottom
    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Utils: Escape HTML
    function escapeHTML(str) {
        if (!str) return "";
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // Utils: Simple Markdown to HTML Parser (Bolds, bullet lists, tables)
    function parseSimpleMarkdown(md) {
        if (!md) return "";
        let html = md;
        
        // Escape HTML tags to protect Layout from breaks
        html = escapeHTML(html);

        // Bold formatting
        html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

        // Suggestion blockquotes
        html = html.replace(/^&gt;\s+(.*)/gm, "<blockquote>$1</blockquote>");

        // Bullet lists
        html = html.replace(/^\s*-\s+(.*)/gm, "<li>$1</li>");
        html = html.replace(/(<li>.*<\/li>)/s, "<ul>$1</ul>");

        // Simple table parsing
        const lines = html.split("\n");
        let inTable = false;
        let tableHTML = "";
        
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            if (line.startsWith("|") && line.endsWith("|")) {
                if (!inTable) {
                    inTable = true;
                    tableHTML += "<table>";
                }
                
                // Skip separator lines e.g. |---|---|
                if (line.match(/^\|[\s:-|]*\|$/)) continue;

                const cells = line.split("|").slice(1, -1);
                tableHTML += "<tr>";
                cells.forEach(cell => {
                    const tag = tableHTML.includes("<tr>") && !tableHTML.includes("</th>") ? "th" : "td";
                    tableHTML += `<${tag}>${cell.trim()}</${tag}>`;
                });
                tableHTML += "</tr>";
            } else {
                if (inTable) {
                    inTable = false;
                    tableHTML += "</table>";
                    lines[i - 1] = tableHTML;
                    tableHTML = "";
                }
            }
        }
        
        if (inTable) {
            tableHTML += "</table>";
            lines[lines.length - 1] = tableHTML;
        }

        return lines.join("\n").replace(/\n/g, "<br>");
    }

    // Render Raw JSON Telemetry Logs
    function renderRawLogs(events) {
        const consoleContent = document.getElementById("raw-logs-content");
        if (!events || events.length === 0) {
            consoleContent.textContent = "No telemetry logs captured.";
            return;
        }
        
        // Map and format each event as structured JSON string line-by-line
        const jsonLines = events.map(ev => JSON.stringify(ev, null, 2)).join("\n\n");
        consoleContent.textContent = jsonLines;
        
        // Scroll the console content to the bottom
        consoleContent.scrollTop = consoleContent.scrollHeight;
    }

    // LOGS MODAL LOGIC
    const logsModal = document.getElementById("logs-modal");
    const showLogsBtn = document.getElementById("show-logs-btn");
    const closeLogsBtn = document.getElementById("close-logs-btn");
    const refreshLogsBtn = document.getElementById("refresh-logs-btn");
    const logsModalBackdrop = document.getElementById("logs-modal-backdrop");
    const logsDate = document.getElementById("logs-date");
    const logsTableBody = document.getElementById("logs-table-body");

    async function fetchAndDisplayLogs() {
        logsTableBody.innerHTML = `<tr><td colspan="3" style="text-align: center; color: var(--text-muted); padding: 24px;"><i class="fa-solid fa-spinner fa-spin" style="margin-right: 8px;"></i> Loading today's logs...</td></tr>`;
        try {
            const res = await fetch("/api/logs");
            if (!res.ok) throw new Error("Failed to fetch logs from server");
            
            const data = await res.json();
            logsDate.textContent = data.date || "Today";
            
            const logs = data.logs || [];
            if (logs.length === 0) {
                logsTableBody.innerHTML = `<tr><td colspan="3" style="text-align: center; color: var(--text-muted); padding: 24px;"><i class="fa-solid fa-circle-info" style="margin-right: 8px;"></i> No logs recorded for today yet. Try running some queries first!</td></tr>`;
                return;
            }
            
            logsTableBody.innerHTML = "";
            logs.forEach(log => {
                const tr = document.createElement("tr");
                
                // Format timestamp HH:mm:ss.SSS
                let timeStr = "--:--:--";
                if (log.timestamp) {
                    if (log.timestamp.includes("T")) {
                        timeStr = log.timestamp.split("T")[1].slice(0, 12);
                    } else {
                        const d = new Date(log.timestamp);
                        if (!isNaN(d.getTime())) {
                            timeStr = d.toTimeString().split(" ")[0] + "." + String(d.getMilliseconds()).padStart(3, '0');
                        }
                    }
                }
                
                const eventType = log.event || "UNKNOWN";
                const eventClass = eventType.toLowerCase();
                
                let detailsHTML = "";
                const logData = log.data || {};
                
                if (eventType === "AGENT_START") {
                    detailsHTML = `
                        <div class="log-details-container">
                            <div><strong>Input Query:</strong></div>
                            <div class="log-detail-section">${escapeHTML(logData.input)}</div>
                            <div class="log-meta-grid">
                                <div class="log-meta-item"><strong>Model:</strong> ${escapeHTML(logData.model)}</div>
                            </div>
                        </div>
                    `;
                } else if (eventType === "AGENT_STEP") {
                    const content = logData.model_response || "";
                    const thoughtMatch = content.match(/Thought:\s*([\s\S]*?)(?:Action:|Final\s*Answer:|$)/i);
                    const thought = thoughtMatch ? thoughtMatch[1].trim() : content;
                    
                    const actionMatch = content.match(/Action:\s*(\w+)\((.*)\)/i);
                    const action = actionMatch ? `${actionMatch[1]}(${actionMatch[2]})` : null;
                    
                    detailsHTML = `
                        <div class="log-details-container">
                            <div><strong>Step ${logData.step} Reasoning:</strong></div>
                            <div class="log-detail-section thought"><strong>Thought:</strong><br>${escapeHTML(thought)}</div>
                            ${action ? `<div class="log-detail-section action"><strong>Action:</strong><br>${escapeHTML(action)}</div>` : ""}
                            <div class="log-meta-grid">
                                <div class="log-meta-item"><strong>Latency:</strong> ${logData.latency_ms ?? 0} ms</div>
                                ${logData.usage ? `
                                    <div class="log-meta-item"><strong>Prompt Tokens:</strong> ${logData.usage.prompt_tokens ?? 0}</div>
                                    <div class="log-meta-item"><strong>Completion Tokens:</strong> ${logData.usage.completion_tokens ?? 0}</div>
                                    <div class="log-meta-item"><strong>Total Tokens:</strong> ${logData.usage.total_tokens ?? 0}</div>
                                ` : ""}
                            </div>
                        </div>
                    `;
                } else if (eventType === "TOOL_EXECUTION") {
                    detailsHTML = `
                        <div class="log-details-container">
                            <div><strong>Tool Call:</strong> <code style="color: var(--accent-cyan); font-family: monospace;">${escapeHTML(logData.tool)}</code></div>
                            <div class="log-detail-section action"><strong>Arguments:</strong><br>${escapeHTML(logData.args)}</div>
                            <div class="log-detail-section observation"><strong>Observation:</strong><br>${escapeHTML(logData.observation)}</div>
                        </div>
                    `;
                } else if (eventType === "AGENT_END") {
                    detailsHTML = `
                        <div class="log-details-container">
                            <div><strong>Agent Finished:</strong></div>
                            <div class="log-detail-section" style="border-left: 3px solid var(--accent-yellow); background: rgba(234, 179, 8, 0.03);"><strong>Final Answer:</strong><br>${escapeHTML(logData.final_answer)}</div>
                            <div class="log-meta-grid">
                                <div class="log-meta-item"><strong>Total Steps:</strong> ${logData.steps ?? 0}</div>
                                <div class="log-meta-item"><strong>Status:</strong> <span style="color: ${logData.status === 'SUCCESS' ? 'var(--accent-green)' : 'var(--accent-red)'}; font-weight: 700;">${logData.status || 'UNKNOWN'}</span></div>
                            </div>
                        </div>
                    `;
                } else {
                    detailsHTML = `
                        <div class="log-details-container">
                            <pre class="log-detail-section">${escapeHTML(JSON.stringify(logData, null, 2))}</pre>
                        </div>
                    `;
                }
                
                tr.innerHTML = `
                    <td class="log-timestamp">${escapeHTML(timeStr)}</td>
                    <td><span class="log-tag ${eventClass}">${escapeHTML(eventType)}</span></td>
                    <td>${detailsHTML}</td>
                `;
                
                logsTableBody.appendChild(tr);
            });
        } catch (err) {
            console.error("Error loading logs:", err);
            logsTableBody.innerHTML = `<tr><td colspan="3" style="text-align: center; color: var(--accent-red); padding: 24px;"><i class="fa-solid fa-triangle-exclamation" style="margin-right: 8px;"></i> Error loading logs: ${escapeHTML(err.message)}</td></tr>`;
        }
    }

    function openLogsModal() {
        logsModal.classList.remove("hidden");
        fetchAndDisplayLogs();
    }

    function closeLogsModal() {
        logsModal.classList.add("hidden");
    }

    showLogsBtn.addEventListener("click", openLogsModal);
    closeLogsBtn.addEventListener("click", closeLogsModal);
    refreshLogsBtn.addEventListener("click", fetchAndDisplayLogs);
    logsModalBackdrop.addEventListener("click", closeLogsModal);

    // Initial Loading trigger
    loadSettings();
});

// Toggle Trace Section Expand/Collapse
function toggleTraceVisibility(el) {
    const traceSteps = el.nextElementSibling;
    traceSteps.classList.toggle("hidden");
    el.classList.toggle("collapsed");
}

// Toggle Step Accordion Expand/Collapse
function toggleStepContent(el) {
    const content = el.nextElementSibling;
    content.classList.toggle("hidden");
    const icon = el.querySelector(".fa-chevron-down");
    if (content.classList.contains("hidden")) {
        icon.style.transform = "rotate(0deg)";
    } else {
        icon.style.transform = "rotate(180deg)";
    }
}

// Toggle Console Panel Expand/Collapse
function toggleConsoleVisibility(el) {
    el.classList.toggle("collapsed");
    const content = el.nextElementSibling;
    content.classList.toggle("collapsed");
}
