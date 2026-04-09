"use client";
import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import Simulation from "@/components/Simulation";

interface Question {
    question: string;
    options: string[];
    correct_index: number;
}

function QuizComponent({ content, onComplete }: { content: string, onComplete: () => void }) {
    const [questions, setQuestions] = useState<Question[]>([]);
    const [loading, setLoading] = useState(false);
    const [score, setScore] = useState<number | null>(null);
    const [answers, setAnswers] = useState<number[]>([]);
    const [showResults, setShowResults] = useState(false);

    const generateQuiz = async () => {
        setLoading(true);
        try {
            const res = await fetch("/api/ai/quiz", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ lesson_content: content }),
            });
            const data = await res.json();
            if (data.questions) {
                setQuestions(data.questions);
                setAnswers(new Array(data.questions.length).fill(-1));
            }
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleAnswer = (qIndex: number, optIndex: number) => {
        const newAnswers = [...answers];
        newAnswers[qIndex] = optIndex;
        setAnswers(newAnswers);
    };

    const submitQuiz = () => {
        let correct = 0;
        questions.forEach((q, i) => {
            if (answers[i] === q.correct_index) correct++;
        });
        setScore(correct);
        setShowResults(true);
        // Mark as complete if they get at least 1 correct (or more strict logic)
        if (correct > 0) {
            onComplete();
        }
    };

    if (loading) return <div className="p-4 border rounded animate-pulse bg-gray-50/50 dark:bg-zinc-800/50 text-white">Generating Quiz...</div>;

    if (questions.length === 0) {
        return (
            <div className="mt-12 border-t border-gray-200 dark:border-gray-700 pt-8">
                <h3 className="text-xl font-bold mb-4 text-gray-800 dark:text-gray-200 uppercase tracking-tight">Challenge Yourself</h3>
                <button
                    onClick={generateQuiz}
                    className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-3 rounded-xl font-bold transition shadow-xl shadow-indigo-500/20 flex items-center gap-2 group"
                >
                    <span className="group-hover:rotate-12 transition">🧠</span> Generate Quiz
                </button>
            </div>
        );
    }

    return (
        <div className="mt-12 border-t border-gray-200 dark:border-gray-700 pt-8 pb-12">
            <h3 className="text-2xl font-bold mb-6 text-indigo-600 dark:text-indigo-400">Knowledge Check</h3>
            <div className="space-y-6">
                {questions.map((q, i) => (
                    <div key={i} className="bg-white/5 backdrop-blur-lg border border-white/10 p-6 rounded-2xl shadow-sm">
                        <p className="font-semibold text-lg mb-4 text-lime-400">{i + 1}. {q.question}</p>
                        <div className="grid gap-3">
                            {q.options.map((opt, j) => {
                                const isSelected = answers[i] === j;
                                let btnClass = "text-left p-4 rounded-xl border transition-all duration-200 text-sm md:text-base ";

                                if (showResults) {
                                    if (j === q.correct_index) btnClass += "bg-green-500/20 border-green-500 text-green-700 dark:text-green-300 font-bold";
                                    else if (isSelected) btnClass += "bg-red-500/20 border-red-500 text-red-700 dark:text-red-300";
                                    else btnClass += "border-gray-200 dark:border-zinc-700 opacity-40";
                                } else {
                                    if (isSelected) btnClass += "bg-indigo-500/10 border-indigo-500 text-indigo-700 dark:text-indigo-300 font-bold ring-2 ring-indigo-500/20";
                                    else btnClass += "hover:bg-white/5 border-gray-200 dark:border-zinc-700 dark:text-gray-300";
                                }

                                return (
                                    <button
                                        key={j}
                                        onClick={() => !showResults && handleAnswer(i, j)}
                                        disabled={showResults}
                                        className={btnClass}
                                    >
                                        {opt}
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                ))}
            </div>

            {!showResults ? (
                <button
                    onClick={submitQuiz}
                    disabled={answers.includes(-1)}
                    className="mt-8 bg-green-600 hover:bg-green-700 text-white px-10 py-4 rounded-2xl font-black disabled:opacity-50 disabled:cursor-not-allowed shadow-xl shadow-green-500/20 transition transform active:scale-95"
                >
                    Complete Quiz
                </button>
            ) : (
                <div className="mt-8 p-8 bg-indigo-500/10 backdrop-blur-xl rounded-3xl text-center border border-indigo-500/30">
                    <h4 className="text-3xl font-black mb-2 text-indigo-700 dark:text-indigo-300">Score: {score} / {questions.length}</h4>
                    <p className="text-gray-600 dark:text-gray-300 font-medium">
                        {score === questions.length ? "Masterpiece! You've mastered this lesson. 🏆" : "Great job! Ready for the next one?"}
                    </p>
                    <button
                        onClick={() => { setQuestions([]); setShowResults(false); setScore(null); }}
                        className="mt-6 text-indigo-500 hover:underline font-bold"
                    >
                        Try Again
                    </button>
                </div>
            )}
        </div>
    );
}

interface Lesson {
    title: string;
    description: string;
}

interface Module {
    title: string;
    lessons: Lesson[];
}

interface CoursePlan {
    course_title: string;
    description: string;
    modules: Module[];
}

function Sidebar({
    coursePlan,
    currentLesson,
    currentModule,
    completedLessons
}: {
    coursePlan: CoursePlan | null,
    currentLesson: string,
    currentModule: string,
    completedLessons: string[]
}) {
    const [collapsed, setCollapsed] = useState(false);

    if (!coursePlan) return null;

    return (
        <div className={`${collapsed ? 'w-16' : 'w-80'} flex-shrink-0 bg-white/10 backdrop-blur-3xl border-r border-white/10 transition-all duration-300 h-screen sticky top-0 overflow-y-auto hidden md:block`}>
            <div className="p-6 border-b border-white/10 flex justify-between items-center">
                {!collapsed && (
                    <h2 className="text-xl font-bold text-white truncate">{coursePlan.course_title}</h2>
                )}
                <button
                    onClick={() => setCollapsed(!collapsed)}
                    className="p-2 hover:bg-white/10 rounded-lg text-white"
                >
                    {collapsed ? "→" : "←"}
                </button>
            </div>
            {!collapsed && (
                <div className="p-4 space-y-6">
                    {coursePlan.modules.map((m, idx) => (
                        <div key={idx}>
                            <h3 className="text-xs font-bold text-indigo-300 uppercase tracking-widest mb-3 px-2">
                                {m.title}
                            </h3>
                            <div className="space-y-1">
                                {m.lessons.map((l, lIdx) => {
                                    const isActive = l.title === currentLesson;
                                    const isCompleted = completedLessons.includes(l.title);
                                    return (
                                        <Link
                                            key={lIdx}
                                            href={`/course/lesson/view?title=${encodeURIComponent(l.title)}&module=${encodeURIComponent(m.title)}`}
                                            className={`flex items-center gap-3 px-3 py-2 rounded-lg transition text-sm ${isActive ? 'bg-white/20 text-white font-bold' : 'text-gray-300 hover:bg-white/5 hover:text-white'}`}
                                        >
                                            <span className={`w-2 h-2 rounded-full ${isCompleted ? 'bg-green-400' : isActive ? 'bg-indigo-400' : 'bg-gray-600'}`}></span>
                                            <span className="truncate">{l.title}</span>
                                            {isCompleted && <span className="ml-auto text-[10px] bg-green-500/20 text-green-400 px-1.5 py-0.5 rounded border border-green-500/30">Done</span>}
                                        </Link>
                                    );
                                })}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

function LessonContent() {
    const searchParams = useSearchParams();
    const lessonTitle = searchParams.get("title");
    const moduleTitle = searchParams.get("module");

    const [content, setContent] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [videoUrl, setVideoUrl] = useState<string | null>(null);
    const [generatingVideo, setGeneratingVideo] = useState(false);
    const [mounted, setMounted] = useState(false);
    const [coursePlan, setCoursePlan] = useState<CoursePlan | null>(null);
    const [completedLessons, setCompletedLessons] = useState<string[]>([]);
    const [activeTab, setActiveTab] = useState<'lesson' | 'practice'>('lesson');
    const [simData, setSimData] = useState<any>(null);

    useEffect(() => {
        setMounted(true);
        // Load progress from localStorage
        const savedProgress = localStorage.getItem("training_hub_progress");
        if (savedProgress) {
            setCompletedLessons(JSON.parse(savedProgress));
        }
        fetchCourseStructure();
    }, []);

    const fetchSimulationData = async () => {
        try {
            // Priority 1: Try live scrape (Fresh content + Full Page capture)
            try {
                const res = await fetch("/api/browser/scrape", { method: "POST" });
                if (res.ok) {
                    const data = await res.json();
                    setSimData(data.data);
                    return;
                }
            } catch (err) {
                console.warn("Live scrape unreachable, attempting fallback...");
            }

            // Priority 2: Fallback to cached snapshot (Offline mode)
            // Use relative path — Next.js rewrites proxy it to the backend
            const snapRes = await fetch("/api/browser/snapshot");
            if (snapRes.ok) {
                const data = await snapRes.json();
                setSimData(data.data);
            }
        } catch (e) {
            console.error("Failed to fetch simulation data:", e);
        }
    };

    const fetchCourseStructure = async () => {
        try {
            const res = await fetch("/api/course/current");
            if (res.ok) {
                const data = await res.json();
                setCoursePlan(data);
            }
        } catch (e) {
            console.error("Failed to fetch course structure:", e);
        }
    };

    const markAsComplete = () => {
        if (!lessonTitle) return;
        if (!completedLessons.includes(lessonTitle)) {
            const nextProgress = [...completedLessons, lessonTitle];
            setCompletedLessons(nextProgress);
            localStorage.setItem("training_hub_progress", JSON.stringify(nextProgress));
        }
    };

    useEffect(() => {
        if (!lessonTitle || !mounted) return;
        generateContent();
        fetchSimulationData();
    }, [lessonTitle, mounted]);

    const generateContent = async () => {
        setLoading(true);
        setError("");
        setVideoUrl(null);
        setGeneratingVideo(false);

        try {
            const res = await fetch("/api/ai/lesson", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    lesson_title: lessonTitle,
                    module_title: moduleTitle || "General"
                }),
            });
            const data = await res.json();

            if (data.status === "generated") {
                setContent(data.content);
            } else {
                setError(data.detail || "Failed to generate content");
            }
        } catch (e) {
            setError("Network error: " + e);
        } finally {
            setLoading(false);
        }
    };

    const generateVideo = async () => {
        if (!content) return;
        setGeneratingVideo(true);
        setVideoUrl(null);

        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 600000);

            const res = await fetch("/api/ai/video", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    title: lessonTitle,
                    text_content: content
                }),
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            const contentType = res.headers.get("content-type") || "";
            if (!contentType.includes("application/json")) {
                const text = await res.text();
                alert("Video Error: Server returned non-JSON response. " + (res.status !== 200 ? `Status: ${res.status}` : text.slice(0, 200)));
                return;
            }

            const data = await res.json();
            if (data.video_url) {
                setVideoUrl(data.video_url);
            } else {
                alert("Internal Video Error: " + (data.detail || "Unknown"));
            }
        } catch (e: any) {
            if (e.name === 'AbortError') {
                alert("Video generation timed out. Please try again with shorter content.");
            } else {
                alert("Video generation failed: " + e);
            }
        } finally {
            setGeneratingVideo(false);
        }
    };

    if (!mounted) return null;
    if (!lessonTitle) return <div className="p-8 text-white">Invalid Lesson Link</div>;

    // Find next lesson
    let nextLessonPath = null;
    if (coursePlan) {
        let foundCurrent = false;
        for (const m of coursePlan.modules) {
            for (const l of m.lessons) {
                if (foundCurrent) {
                    nextLessonPath = `/course/lesson/view?title=${encodeURIComponent(l.title)}&module=${encodeURIComponent(m.title)}`;
                    break;
                }
                if (l.title === lessonTitle) foundCurrent = true;
            }
            if (nextLessonPath) break;
        }
    }

    return (
        <div className="flex bg-gray-900 min-h-screen text-gray-100 selection:bg-indigo-500/30">
            <Sidebar
                coursePlan={coursePlan}
                currentLesson={lessonTitle}
                currentModule={moduleTitle || ""}
                completedLessons={completedLessons}
            />

            <div className="flex-1 overflow-y-auto h-screen relative bg-gradient-to-br from-indigo-950 via-gray-900 to-black">
                {/* Modern Header Nav */}
                <header className="sticky top-0 z-20 bg-black/40 backdrop-blur-xl border-b border-white/5 p-4 flex justify-between items-center transition-all duration-500">
                    <div className="flex items-center gap-4">
                        <Link href="/course/viewer" className="p-2 hover:bg-white/5 rounded-full transition text-gray-400 hover:text-white">
                            ←
                        </Link>
                        <div>
                            <p className="text-[10px] font-black uppercase tracking-widest text-indigo-400 opacity-80">{moduleTitle}</p>
                            <h1 className="text-lg font-bold truncate max-w-sm">{lessonTitle}</h1>
                        </div>
                    </div>

                    {/* Premium Tab Switcher */}
                    <div className="flex bg-white/5 p-1 rounded-xl border border-white/10 shadow-inner">
                        <button
                            onClick={() => setActiveTab('lesson')}
                            className={`px-6 py-2 rounded-lg text-xs font-black uppercase tracking-widest transition-all duration-300 ${activeTab === 'lesson' ? 'bg-indigo-600 text-white shadow-lg' : 'text-gray-500 hover:text-gray-300'}`}
                        >
                            Theory
                        </button>
                        <button
                            onClick={() => setActiveTab('practice')}
                            className={`px-6 py-2 rounded-lg text-xs font-black uppercase tracking-widest transition-all duration-300 ${activeTab === 'practice' ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/20' : 'text-gray-500 hover:text-gray-300'}`}
                        >
                            Practice
                        </button>
                    </div>

                    <div className="flex items-center gap-3">
                        {content && (
                            <button
                                onClick={generateVideo}
                                disabled={generatingVideo || !!videoUrl}
                                className="bg-white text-black hover:bg-gray-200 disabled:opacity-50 px-4 py-2 rounded-xl font-bold transition flex items-center gap-2 text-[10px] shadow-lg"
                            >
                                {generatingVideo ? 'Synthesizing...' : videoUrl ? 'Video Ready' : '🎬 Create Video'}
                            </button>
                        )}
                        <button onClick={generateContent} className="p-2 hover:bg-white/5 rounded-xl transition text-gray-400" title="Regenerate">
                            🔄
                        </button>
                    </div>
                </header>

                <main className="p-6 md:p-12 max-w-5xl mx-auto">
                    {loading ? (
                        <div className="flex flex-col items-center justify-center py-32 space-y-8">
                            <div className="w-12 h-12 border-4 border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin"></div>
                            <p className="text-xl font-medium animate-pulse text-indigo-300 tracking-tighter">AI Instructor is building your sandbox...</p>
                        </div>
                    ) : error ? (
                        <div className="p-12 bg-red-500/10 border border-red-500/30 rounded-3xl text-center shadow-2xl">
                            <h3 className="text-2xl font-bold text-red-400 mb-4">Pipeline Break</h3>
                            <p className="text-red-300/80 mb-8">{error}</p>
                            <button onClick={generateContent} className="px-8 py-3 bg-red-500 hover:bg-red-600 text-white rounded-xl font-bold">
                                Try Again
                            </button>
                        </div>
                    ) : (
                        <div className="space-y-12">
                            {activeTab === 'lesson' ? (
                                <>
                                    {/* Video Section with Glass Finish */}
                                    {(generatingVideo || videoUrl) && (
                                        <section className="relative group">
                                            {generatingVideo && (
                                                <div className="aspect-video w-full rounded-3xl overflow-hidden bg-white/5 border border-white/10 flex flex-col items-center justify-center space-y-4 animate-in fade-in zoom-in duration-500">
                                                    <div className="w-16 h-16 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin shadow-[0_0_30px_rgba(99,102,241,0.3)]"></div>
                                                    <div className="text-center">
                                                        <h3 className="text-xl font-bold text-white uppercase tracking-tighter">Synthesizing Sora Clips...</h3>
                                                        <p className="text-indigo-300/60 text-xs">Several minutes required for high-fidelity rendering</p>
                                                    </div>
                                                </div>
                                            )}
                                            {videoUrl && !generatingVideo && (
                                                <div className="rounded-3xl overflow-hidden shadow-[0_0_100px_rgba(0,0,0,0.5)] border border-white/10 p-1 bg-white/5">
                                                    <video controls className="w-full aspect-video rounded-2xl bg-black shadow-inner" src={videoUrl}>
                                                        Your browser does not support the video tag.
                                                    </video>
                                                    <div className="p-4 flex justify-between items-center text-xs font-black uppercase tracking-widest text-gray-500">
                                                        <span>AI-Enhanced Video Summary</span>
                                                        <span className="text-green-500">Sora V2 High Detail</span>
                                                    </div>
                                                </div>
                                            )}
                                        </section>
                                    )}

                                    {/* Content Section */}
                                    <article className="prose prose-invert prose-indigo max-w-none
                                        prose-headings:font-black prose-headings:tracking-tighter
                                        prose-h2:text-4xl prose-h2:mb-8 prose-h2:text-white
                                        prose-p:text-gray-300 prose-p:leading-relaxed prose-lg
                                        prose-strong:text-indigo-400
                                        prose-code:text-pink-400 prose-code:bg-white/5 prose-code:px-2 prose-code:py-0.5 prose-code:rounded-md prose-code:before:content-none prose-code:after:content-none
                                        prose-pre:bg-black/40 prose-pre:border prose-pre:border-white/5 prose-pre:rounded-3xl
                                        prose-img:rounded-3xl prose-img:shadow-2xl
                                    ">
                                        <ReactMarkdown>{content || ""}</ReactMarkdown>
                                    </article>

                                    {/* Interaction Hub */}
                                    <section className="mt-20 pt-12 border-t border-white/5">
                                        <QuizComponent content={content || ""} onComplete={markAsComplete} />
                                    </section>
                                </>
                            ) : (
                                <section className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                                    <div className="bg-indigo-500/10 border border-indigo-500/20 p-10 rounded-3xl flex items-center justify-between">
                                        <div>
                                            <h2 className="text-3xl font-black text-white italic tracking-tighter">Practical Sandbox</h2>
                                            <p className="text-indigo-300/60 text-sm font-medium">Click on the dynamic hotspots to complete the workflow task.</p>
                                        </div>
                                        <div className="hidden lg:block">
                                            <div className="flex items-center gap-2">
                                                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                                                <span className="text-[10px] text-green-400 px-3 py-1 rounded-full border border-green-500/30 uppercase font-black tracking-widest">Live Capture Sync</span>
                                            </div>
                                        </div>
                                    </div>
                                    {simData ? (
                                        <Simulation
                                            screenshotUrl={`/api/browser/screenshot/${simData.screenshot?.split(/[/\\]/).pop() || ''}`}
                                            hotspots={simData.interactive_elements}
                                            onSuccess={() => {
                                                alert("Action verified! Skill unlocked. 🎉");
                                                markAsComplete();
                                            }}
                                        />
                                    ) : (
                                        <div className="aspect-video w-full flex flex-col items-center justify-center space-y-6 bg-white/5 rounded-3xl border border-white/10 animate-pulse border-dashed">
                                            <div className="w-10 h-10 border-2 border-indigo-500/40 border-t-indigo-500 rounded-full animate-spin"></div>
                                            <p className="text-indigo-300/40 text-[10px] font-black uppercase tracking-widest">Warming up the testing range...</p>
                                        </div>
                                    )}
                                </section>
                            )}
                        </div>
                    )}
                </main>

                <footer className="mt-20 flex flex-col md:flex-row gap-6 p-8 bg-white/5 border border-white/10 rounded-3xl items-center justify-between mx-6 md:mx-12 mb-12">
                    <div className="flex items-center gap-4">
                        <div className={`p-4 rounded-full ${completedLessons.includes(lessonTitle) ? 'bg-green-500' : 'bg-gray-800'} text-white text-2xl`}>
                            {completedLessons.includes(lessonTitle) ? '✓' : '📖'}
                        </div>
                        <div>
                            <h4 className="text-xl font-bold text-white">{completedLessons.includes(lessonTitle) ? 'Lesson Mastered!' : 'Finish this lesson'}</h4>
                            <p className="text-gray-400 text-sm">{completedLessons.includes(lessonTitle) ? 'You’ve reached the goal for this tutorial.' : 'Complete the quiz to mark it as finished.'}</p>
                        </div>
                    </div>
                    {nextLessonPath ? (
                        <Link
                            href={nextLessonPath}
                            className="bg-indigo-600 hover:bg-indigo-500 text-white px-8 py-4 rounded-2xl font-black shadow-xl shadow-indigo-600/20 transition group"
                        >
                            Next Lesson <span className="inline-block group-hover:translate-x-2 transition ml-2">→</span>
                        </Link>
                    ) : (
                        <Link
                            href="/course/viewer"
                            className="bg-white/10 hover:bg-white/20 text-white px-8 py-4 rounded-2xl font-black transition"
                        >
                            Back to Dashboard
                        </Link>
                    )}
                </footer>
            </div>
        </div>
    );
}

export default function LessonPage() {
    return (
        <Suspense fallback={<div>Loading...</div>}>
            <LessonContent />
        </Suspense>
    )
}
