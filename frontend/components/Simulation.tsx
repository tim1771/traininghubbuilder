"use client";
import { useState, useRef, useEffect } from "react";

interface Hotspot {
    text: string;
    x: number;
    y: number;
    width: number;
    height: number;
    type: string;
}

interface SimulationProps {
    screenshotUrl: string;
    hotspots: Hotspot[];
    onSuccess: () => void;
}

export default function Simulation({ screenshotUrl, hotspots, onSuccess }: SimulationProps) {
    const [target, setTarget] = useState<Hotspot | null>(null);
    const [feedback, setFeedback] = useState<{ x: number, y: number, type: 'success' | 'fail' } | null>(null);
    const [imgLoaded, setImgLoaded] = useState(false);
    const [imgError, setImgError] = useState(false);
    const imgRef = useRef<HTMLImageElement>(null);

    useEffect(() => {
        if (hotspots && hotspots.length > 0) {
            const randomTarget = hotspots[Math.floor(Math.random() * hotspots.length)];
            setTarget(randomTarget);
        }
    }, [hotspots]);

    const handleClick = (e: React.MouseEvent) => {
        if (!imgRef.current || !target) return;

        const rect = imgRef.current.getBoundingClientRect();

        // Calculate coordinates relative to the original image size
        const clickX = (e.clientX - rect.left) * (imgRef.current.naturalWidth / rect.width);
        const clickY = (e.clientY - rect.top) * (imgRef.current.naturalHeight / rect.height);

        // Check if click is within target bounds
        const isCorrect =
            clickX >= target.x &&
            clickX <= target.x + target.width &&
            clickY >= target.y &&
            clickY <= target.y + target.height;

        setFeedback({ x: e.clientX - rect.left, y: e.clientY - rect.top, type: isCorrect ? 'success' : 'fail' });

        if (isCorrect) {
            setTimeout(() => {
                setFeedback(null);
                onSuccess();
            }, 1000);
        } else {
            setTimeout(() => setFeedback(null), 800);
        }
    };

    if (!target) return (
        <div className="p-12 text-center bg-gray-50 dark:bg-white/5 rounded-3xl border border-gray-200 dark:border-white/10 space-y-4">
            <p className="text-gray-500 dark:text-gray-400">Waiting for simulation coordinates...</p>
            <div className="w-8 h-8 border-2 border-indigo-500/40 border-t-indigo-500 rounded-full animate-spin mx-auto"></div>
        </div>
    );

    if (imgError) return (
        <div className="p-12 text-center bg-gray-50 dark:bg-white/5 rounded-3xl border border-gray-200 dark:border-white/10 space-y-4 min-h-[400px] flex flex-col items-center justify-center">
            <p className="text-red-600 dark:text-red-400 font-bold">Screenshot failed to load</p>
            <p className="text-gray-500 text-sm">Try scraping the page again from the home screen.</p>
        </div>
    );

    return (
        <div className="relative rounded-3xl overflow-hidden border border-white/10 shadow-2xl bg-black group select-none min-h-[400px] w-full">
            {/* HUD Header - Fixed */}
            <div className="absolute top-6 left-1/2 -translate-x-1/2 z-40 bg-black/60 backdrop-blur-md px-6 py-3 rounded-2xl border border-white/20 text-center shadow-2xl animate-bounce pointer-events-none">
                <p className="text-indigo-300 text-xs font-black uppercase tracking-widest mb-1">Practice Task</p>
                <p className="text-white font-bold text-lg">Click on: <span className="text-indigo-400">&quot;{target.text}&quot;</span></p>
            </div>

            {/* Loading state */}
            {!imgLoaded && (
                <div className="absolute inset-0 flex items-center justify-center z-20">
                    <div className="w-10 h-10 border-2 border-indigo-500/40 border-t-indigo-500 rounded-full animate-spin"></div>
                </div>
            )}

            {/* Scrollable Viewport */}
            <div className="max-h-[75vh] overflow-y-auto overflow-x-hidden relative scrollbar-thin scrollbar-thumb-white/20 scrollbar-track-transparent">
                <div className="relative">
                    <img
                        ref={imgRef}
                        src={screenshotUrl}
                        alt="Simulation"
                        className={`w-full h-auto cursor-crosshair group-hover:opacity-100 transition duration-500 block ${imgLoaded ? 'opacity-80' : 'opacity-0'}`}
                        onClick={handleClick}
                        onLoad={() => setImgLoaded(true)}
                        onError={() => setImgError(true)}
                    />

                    {feedback && (
                        <div
                            className="absolute w-12 h-12 rounded-full border-4 flex items-center justify-center animate-ping-once pointer-events-none z-30"
                            style={{ left: feedback.x - 24, top: feedback.y - 24, borderColor: feedback.type === 'success' ? '#4ade80' : '#f87171' }}
                        >
                            <span className="text-2xl">{feedback.type === 'success' ? '✅' : '❌'}</span>
                        </div>
                    )}
                </div>
            </div>

            {/* HUD Footer - Fixed */}
            <div className="absolute bottom-6 left-6 right-6 flex justify-between items-center transition duration-300 z-40 bg-gradient-to-t from-black/80 to-transparent pb-2">
                <span className="text-white/40 text-[10px] uppercase font-black tracking-widest">Interactive Sandbox Mode</span>
                <button
                    onClick={() => {
                        if (hotspots && hotspots.length > 0) {
                            setTarget(hotspots[Math.floor(Math.random() * hotspots.length)])
                        }
                    }}
                    className="text-indigo-400 hover:text-white text-xs font-bold transition bg-black/50 px-3 py-1 rounded-lg backdrop-blur-sm border border-white/10"
                >
                    Skip to another task
                </button>
            </div>
        </div>
    );
}
