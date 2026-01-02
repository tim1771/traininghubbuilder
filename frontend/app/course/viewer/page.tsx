"use client";
import { useEffect, useState } from "react";
import Link from "next/link";

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

export default function CourseViewer() {
    const [course, setCourse] = useState<CoursePlan | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch("/api/course/current")
            .then((res) => {
                if (!res.ok) throw new Error("Failed to load course");
                return res.json();
            })
            .then((data) => setCourse(data))
            .catch((err) => console.error(err))
            .finally(() => setLoading(false));
    }, []);

    if (loading) return <div className="p-10 text-center">Loading Course...</div>;
    if (!course) return (
        <div className="min-h-screen flex flex-col items-center justify-center p-8 space-y-4">
            <h2 className="text-2xl font-bold text-red-600">Course Plan Not Found</h2>
            <p className="text-gray-600">It seems the course hasn't been generated yet or was lost.</p>
            <Link href="/" className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition">
                &larr; Go Back to Builder
            </Link>
        </div>
    );

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-zinc-900 text-gray-900 dark:text-gray-100 p-8">
            <div className="max-w-4xl mx-auto">
                <div className="mb-8">
                    <Link href="/" className="text-blue-500 hover:underline mb-4 inline-block">&larr; Back to Builder</Link>
                    <h1 className="text-4xl font-bold mb-2">{course.course_title}</h1>
                    <p className="text-xl text-gray-600 dark:text-gray-400">{course.description}</p>
                </div>

                <div className="space-y-6">
                    {course.modules.map((mod, i) => (
                        <div key={i} className="bg-white dark:bg-zinc-800 rounded-lg shadow-md p-6">
                            <h2 className="text-2xl font-semibold mb-4 border-b pb-2 dark:border-zinc-700">
                                {mod.title}
                            </h2>
                            <div className="grid gap-3">
                                {mod.lessons.map((lesson, j) => (
                                    <div key={j} className="p-4 bg-gray-50 dark:bg-zinc-700/50 rounded flex justify-between items-center group hover:bg-blue-50 dark:hover:bg-blue-900/20 transition">
                                        <div>
                                            <h3 className="font-medium text-lg">{lesson.title}</h3>
                                            <p className="text-sm text-gray-500 dark:text-gray-400">{lesson.description}</p>
                                        </div>
                                        <Link
                                            href={`/course/lesson/view?title=${encodeURIComponent(lesson.title)}&module=${encodeURIComponent(mod.title)}`}
                                            className="px-4 py-2 bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 rounded text-sm font-semibold opacity-0 group-hover:opacity-100 transition"
                                        >
                                            Start Lesson
                                        </Link>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>

                <div className="mt-12 text-center">
                    <button className="bg-green-600 hover:bg-green-700 text-white font-bold py-3 px-8 rounded-lg shadow transition transform hover:scale-105">
                        Download JSON (Coming Soon)
                    </button>
                </div>
            </div>
        </div>
    );
}
