"use client";
import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import ReactMarkdown from "react-markdown";

interface Question {
    question: string;
    options: string[];
    correct_index: number;
}

function QuizComponent({ content }: { content: string }) {
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
    };

    if (loading) return <div className="p-4 border rounded animate-pulse bg-gray-50">Generating Quiz...</div>;

    if (questions.length === 0) {
        return (
            <div className="mt-12 border-t border-gray-200 dark:border-gray-700 pt-8">
                <h3 className="text-xl font-bold mb-4 text-gray-800 dark:text-gray-200">Test Your Knowledge</h3>
                <button
                    onClick={generateQuiz}
                    className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-3 rounded-lg font-semibold transition shadow-md shadow-indigo-500/30 flex items-center gap-2"
                >
                    🧠 Generate Quiz for this Lesson
                </button>
            </div>
        );
    }

    return (
        <div className="mt-12 border-t border-gray-200 dark:border-gray-700 pt-8 pb-12">
            <h3 className="text-2xl font-bold mb-6 text-indigo-600 dark:text-indigo-400">Quiz Time</h3>
            <div className="space-y-8">
                {questions.map((q, i) => (
                    <div key={i} className="bg-gray-50/50 dark:bg-zinc-800/50 p-6 rounded-xl shadow-sm border border-gray-100 dark:border-zinc-700">
                        <p className="font-medium text-lg mb-4 text-gray-800 dark:text-gray-200">{i + 1}. {q.question}</p>
                        <div className="grid gap-2">
                            {q.options.map((opt, j) => {
                                const isSelected = answers[i] === j;
                                let btnClass = "text-left p-3 rounded-lg border transition duration-200 text-sm md:text-base ";

                                if (showResults) {
                                    if (j === q.correct_index) btnClass += "bg-green-100 border-green-500 text-green-800 dark:bg-green-900/40 dark:text-green-200 font-semibold";
                                    else if (isSelected) btnClass += "bg-red-100 border-red-500 text-red-800 dark:bg-red-900/40 dark:text-red-200";
                                    else btnClass += "border-gray-200 dark:border-zinc-700 opacity-60";
                                } else {
                                    if (isSelected) btnClass += "bg-indigo-100 border-indigo-500 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-200 font-medium transform scale-[1.01]";
                                    else btnClass += "hover:bg-gray-100 dark:hover:bg-zinc-700 border-gray-200 dark:border-zinc-700 dark:text-gray-300";
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
                    className="mt-6 bg-green-600 hover:bg-green-700 text-white px-8 py-3 rounded-lg font-bold disabled:opacity-50 disabled:cursor-not-allowed shadow-lg transition transform hover:scale-105"
                >
                    Submit Answers
                </button>
            ) : (
                <div className="mt-8 p-6 bg-blue-50 dark:bg-blue-900/20 rounded-xl text-center border border-blue-100 dark:border-blue-900/50">
                    <h4 className="text-2xl font-bold mb-2 text-blue-800 dark:text-blue-300">You scored {score} / {questions.length}</h4>
                    <p className="text-gray-600 dark:text-gray-300">
                        {score === questions.length ? "Perfect score! 🎉" : "Good effort! Review the lesson and try again."}
                    </p>
                    <button
                        onClick={() => { setQuestions([]); setShowResults(false); setScore(null); }}
                        className="mt-4 text-blue-600 dark:text-blue-400 hover:underline font-medium"
                    >
                        Reset Quiz
                    </button>
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

    useEffect(() => {
        if (!lessonTitle) return;
        generateContent();
    }, [lessonTitle]);

    const generateContent = async () => {
        setLoading(true);
        setError("");

        // Reset video states when generating new content
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
        setVideoUrl(null); // Clear any existing video

        try {
            const res = await fetch("/api/ai/video", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    title: lessonTitle,
                    text_content: content
                }),
            });
            const data = await res.json();
            if (data.video_url) {
                // Video is ready, display it
                setVideoUrl(data.video_url);
            } else {
                alert("Internal Video Error: " + (data.detail || "Unknown"));
            }
        } catch (e) {
            alert("Video generation failed: " + e);
        } finally {
            setGeneratingVideo(false);
        }
    };

    if (!lessonTitle) return <div className="p-8">Invalid Lesson Link</div>;

    return (
        <div className="min-h-screen bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 dark:from-indigo-900 dark:via-purple-900 dark:to-pink-900 p-6 md:p-12">
            <div className="max-w-4xl mx-auto bg-white/90 dark:bg-black/80 backdrop-blur-xl rounded-2xl shadow-2xl overflow-hidden border border-white/20">

                {/* Header */}
                <div className="p-8 border-b border-gray-200 dark:border-gray-700 bg-white/50 dark:bg-white/5">
                    <div className="flex justify-between items-start">
                        <div>
                            <Link href="/course/viewer" className="text-indigo-600 dark:text-indigo-400 hover:underline text-sm font-semibold mb-2 block tracking-wider uppercase">
                                &larr; Back to Course
                            </Link>
                            <h5 className="text-gray-500 dark:text-gray-400 text-xs font-bold uppercase tracking-widest mb-1">{moduleTitle}</h5>
                            <h1 className="text-3xl md:text-5xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-gray-900 to-gray-600 dark:from-white dark:to-gray-300">
                                {lessonTitle}
                            </h1>
                        </div>
                        <div className="flex gap-2">
                            {content && (
                                <button
                                    onClick={generateVideo}
                                    disabled={generatingVideo || !!videoUrl}
                                    className="bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg font-bold transition flex items-center gap-2 text-sm shadow-lg"
                                >
                                    {generatingVideo ? (
                                        <><span>🎥</span> Creating Video...</>
                                    ) : videoUrl ? (
                                        <><span>✅</span> Video Ready</>
                                    ) : (
                                        <><span>🎬</span> Create Video</>
                                    )}
                                </button>
                            )}
                            <button
                                onClick={generateContent}
                                className="bg-white/20 hover:bg-white/40 p-2 rounded-full transition backdrop-blur-sm text-gray-700 dark:text-gray-200"
                                title="Regenerate Lesson"
                            >
                                🔄
                            </button>
                        </div>
                    </div>
                </div>

                {/* Content Area */}
                <div className="p-8 md:p-12">
                    {loading ? (
                        <div className="flex flex-col items-center justify-center py-20 space-y-6">
                            <div className="relative">
                                <div className="w-16 h-16 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
                                <div className="absolute inset-0 flex items-center justify-center text-2xl">🤖</div>
                            </div>
                            <div className="text-center">
                                <p className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-500 to-purple-600 animate-pulse">
                                    AI Instructor is crafting your lesson...
                                </p>
                                <p className="text-sm text-gray-500 mt-2">Analyzing context & writing tutorial...</p>
                            </div>
                        </div>
                    ) : error ? (
                        <div className="p-8 bg-red-50/90 dark:bg-red-900/30 border border-red-200 rounded-xl text-center">
                            <h3 className="text-xl font-bold text-red-700 dark:text-red-400 mb-2">Generation Failed</h3>
                            <p className="text-red-600 dark:text-red-300 mb-6">{error}</p>
                            <button onClick={generateContent} className="px-6 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-semibold transition shadow-lg shadow-red-500/30">
                                Try Again
                            </button>
                        </div>
                    ) : (
                        <>
                            {/* Video Generation Loading Overlay */}
                            {generatingVideo && (
                                <div className="mb-12 rounded-xl overflow-hidden shadow-2xl border-4 border-purple-500/30 bg-gradient-to-br from-purple-900/90 to-indigo-900/90 p-12">
                                    <div className="flex flex-col items-center justify-center space-y-6">
                                        <div className="relative">
                                            <div className="w-20 h-20 border-4 border-purple-400 border-t-transparent rounded-full animate-spin"></div>
                                            <div className="absolute inset-0 flex items-center justify-center text-3xl">🎬</div>
                                        </div>
                                        <div className="text-center">
                                            <h3 className="text-2xl font-bold text-white mb-2">Generating Your Video...</h3>
                                            <p className="text-purple-200">Please wait while we create your AI-powered lesson video</p>
                                            <p className="text-purple-300 text-sm mt-2">This may take 30-60 seconds</p>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Video Player Section */}
                            {videoUrl && !generatingVideo && (
                                <div className="mb-12 rounded-xl overflow-hidden shadow-2xl border-4 border-purple-500/30 animate-fade-in-down">
                                    <video controls className="w-full aspect-video bg-black" src={`http://localhost:8000${videoUrl}`}>
                                        Your browser does not support the video tag.
                                    </video>
                                    <div className="p-3 bg-purple-100 dark:bg-purple-900/40 text-center text-sm font-semibold text-purple-800 dark:text-purple-200">
                                        ✨ AI-Generated Video Summary
                                    </div>
                                </div>
                            )}

                            <div className="prose dark:prose-invert prose-lg max-w-none 
                                prose-headings:font-bold prose-headings:tracking-tight prose-headings:text-gray-900 dark:prose-headings:text-gray-100
                                prose-h2:text-3xl prose-h2:mt-12 prose-h2:mb-6 prose-h2:text-indigo-600 dark:prose-h2:text-indigo-400
                                prose-strong:font-extrabold prose-strong:text-indigo-700 dark:prose-strong:text-indigo-300
                                prose-img:rounded-xl prose-img:shadow-lg
                                prose-code:text-pink-600 dark:prose-code:text-pink-400 prose-code:bg-pink-50 dark:prose-code:bg-pink-900/20 prose-code:px-1 prose-code:rounded
                                prose-pre:bg-gray-900 prose-pre:shadow-xl prose-pre:rounded-xl
                            ">
                                <ReactMarkdown
                                    components={{
                                        // Custom styling for bold steps or lists
                                    }}
                                >
                                    {content || ""}
                                </ReactMarkdown>
                            </div>

                            {/* Quiz Section */}
                            {content && (
                                <div className="mt-16 animate-fade-in-up">
                                    <QuizComponent content={content} />
                                </div>
                            )}
                        </>
                    )}
                </div>
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
