// Frontend Controller - ReAct Agent Web Playground

document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const llmProvider = document.getElementById("llm-provider");
    const modelName = document.getElementById("model-name");
    const maxSteps = document.getElementById("max-steps");
    const stepsVal = document.getElementById("steps-val");
    const systemPrompt = document.getElementById("system-prompt");
    const settingsForm = document.getElementById("settings-form");
    
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
                systemPrompt.value = data.system_prompt || "";
                
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
            system_prompt: systemPrompt.value,
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
            if (res.ok) {
                showNotification("Agent customization applied successfully!");
            } else {
                showNotification("Failed to save settings.");
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
