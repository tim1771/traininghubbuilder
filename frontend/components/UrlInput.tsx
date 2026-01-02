"use client";

import { useState } from "react";

export default function UrlInput() {
    const [url, setUrl] = useState("");
    const [loading, setLoading] = useState(false);
    const [status, setStatus] = useState("");

    const handleLearnMode = async () => {
        setLoading(true);
        setStatus("Launching browser for Learn Mode...");
        try {
            // Launch browser (headless=false so user can interact)
            await fetch("/api/browser/launch", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ headless: false, use_auth: false }),
            });

            setStatus("Browser open. Please log in to the target site.");

            if (url) {
                await fetch("/api/browser/navigate", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ url }),
                });
            }

            // In a real app, we'd poll or separate this step
            // For now, let's just leave it open or provide a "Save Auth" button
            setStatus("Login in the popup window. Click 'Save Session' when done.");

        } catch (e) {
            console.error(e);
            setStatus("Error: " + e);
        } finally {
            setLoading(false);
        }
    };

    const saveSession = async () => {
        try {
            const res = await fetch("/api/browser/save-auth", { method: "POST" });
            const data = await res.json();
            if (data.status === "saved") {
                setStatus("Session saved! You can now run in Headless mode.");
                await fetch("/api/browser/close", { method: "POST" });
            }
        } catch (e) {
            setStatus("Error saving session: " + e);
        }
    };

    const handleStartScrape = async () => {
        setLoading(true);
        setStatus("Starting scraper...");
        try {
            // Launch headless with auth
            await fetch("/api/browser/launch", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ headless: true, use_auth: true }),
            });

            setStatus("Navigating...");
            await fetch("/api/browser/navigate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ url }),
            });

            setStatus("Scraping content...");
            const res = await fetch("/api/browser/scrape", { method: "POST" });
            const data = await res.json();

            console.log("Scraped Data:", data);
            setStatus("Scrape complete! Click 'Generate Curriculum' to proceed.");

        } catch (e) {
            console.error(e);
            setStatus("Error: " + e);
        } finally {
            setLoading(false);
        }
    };

    const handleGenerateCurriculum = async () => {
        setLoading(true);
        setStatus("Generating course curriculum with AI...");
        try {
            const res = await fetch("/api/ai/plan", { method: "POST" });
            const data = await res.json();

            console.log("Generated Plan Response:", data);

            // Check for success status OR valid plan data
            if (data.status === "planned" || (data.plan && data.plan.course_title)) {
                setStatus(`Success! Redirecting to course viewer...`);
                // Force redirect after short delay to let user see success msg
                setTimeout(() => {
                    window.location.href = "/course/viewer";
                }, 1000);
            } else if (data.error) {
                setStatus(`Error: ${data.error}`);
            } else if (data.detail) {
                // FastAPI standard error
                setStatus(`Backend Error: ${data.detail}`);
            } else {
                setStatus(`Unknown response: ${JSON.stringify(data)}`);
            }

        } catch (e) {
            console.error(e);
            setStatus("Error generating curriculum: " + e);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="w-full max-w-xl mx-auto p-6 bg-white dark:bg-zinc-800 rounded-xl shadow-lg space-y-4">
            <div className="flex flex-col space-y-2">
                <label htmlFor="url" className="text-sm font-medium">Target Website URL</label>
                <input
                    id="url"
                    type="url"
                    placeholder="https://example.com"
                    className="p-3 rounded-md border border-zinc-300 dark:border-zinc-700 bg-transparent"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                />
            </div>

            <div className="flex space-x-4">
                <button
                    onClick={handleStartScrape}
                    disabled={loading || !url}
                    className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded disabled:opacity-50"
                >
                    {loading ? "Working..." : "Auto-Build Course"}
                </button>

                <button
                    onClick={handleLearnMode}
                    className="flex-1 bg-amber-500 hover:bg-amber-600 text-white font-bold py-2 px-4 rounded"
                >
                    Teach / Login
                </button>
            </div>

            {status.includes("Login in") && (
                <button
                    onClick={saveSession}
                    className="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded animate-pulse"
                >
                    Start Recording / Save Session
                </button>
            )}

            {status.includes("Scrape complete") && (
                <button
                    onClick={handleGenerateCurriculum}
                    disabled={loading}
                    className="w-full bg-purple-600 hover:bg-purple-700 text-white font-bold py-2 px-4 rounded disabled:opacity-50"
                >
                    {loading ? "Generating..." : "🤖 Generate Curriculum"}
                </button>
            )}

            {status && (
                <div className="p-3 bg-zinc-100 dark:bg-zinc-900 rounded text-sm font-mono break-words">
                    &gt; {status}
                </div>
            )}
        </div>
    );
}
