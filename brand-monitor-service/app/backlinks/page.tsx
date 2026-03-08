"use client";

import dynamic from "next/dynamic";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Loader2 } from "lucide-react";
import { Suspense } from "react";

const SEOBacklinksTab = dynamic(
    () => import("@/components/brand-monitor/seo-backlinks-tab").then((m) => m.SEOBacklinksTab),
    { ssr: false }
);

function BacklinksContent() {
    const searchParams = useSearchParams();
    const brandId = searchParams.get("brandId");

    return (
        <div className="min-h-screen bg-slate-50 relative overflow-hidden bg-grid-zinc-100">
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute -top-24 -left-24 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl animate-blob" />
                <div className="absolute top-1/2 right-0 w-[500px] h-[500px] bg-purple-500/10 rounded-full blur-3xl animate-blob animation-delay-2000" />
            </div>
            {/* Floating Back Button */}
            <div className="absolute top-4 left-4 sm:left-6 lg:left-8 z-50">
                <Link
                    href={brandId ? `/brand-profiles/${brandId}` : "/brand-profiles"}
                    className="inline-flex items-center gap-2 text-sm font-medium text-slate-600 hover:text-slate-900 transition-all bg-white/80 backdrop-blur-md px-4 py-2 rounded-full border border-slate-200/60 hover:bg-white hover:border-slate-300 hover:shadow-md hover:-translate-y-0.5"
                >
                    <ArrowLeft className="w-4 h-4" />
                    Back to Profile
                </Link>
            </div>

            {/* Main Content */}
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 pt-20">
                <SEOBacklinksTab brandId={brandId || undefined} />
            </div>
        </div>
    );
}

export default function BacklinksPage() {
    return (
        <Suspense fallback={
            <div className="min-h-screen flex items-center justify-center bg-slate-50">
                <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
            </div>
        }>
            <BacklinksContent />
        </Suspense>
    );
}
