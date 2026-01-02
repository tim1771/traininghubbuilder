"use client";
import { useEffect, useState } from "react";


import UrlInput from "@/components/UrlInput";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-zinc-50 font-sans dark:bg-black text-black dark:text-white p-8">
      <div className="max-w-2xl w-full space-y-8">
        <StatusCheck />
        <UrlInput />
      </div>
    </div>
  );
}

function StatusCheck() {
  const [status, setStatus] = useState<string>("Checking backend...");

  useEffect(() => {
    fetch("/api_root")
      .then((res) => res.json())
      .then((data) => setStatus(data.message))
      .catch((err) => {
        console.error("Connection failed:", err);
        setStatus(`Backend not connected: ${err.message}`);
      });
  }, []);

  return (
    <div className="text-center space-y-4">
      <h1 className="text-4xl font-bold">Training Hub Builder</h1>
      <p className="text-xl">System Status: <span className={status.includes("Live") ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"}>{status}</span></p>
    </div>
  );

}
