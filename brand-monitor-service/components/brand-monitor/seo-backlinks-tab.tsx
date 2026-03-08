'use client';

import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Loader2, ExternalLink, TrendingUp, Link as LinkIcon, Globe, AlertCircle, RefreshCw, ChevronDown, ChevronUp, Edit, X } from 'lucide-react';
import type { CompetitorBacklinkData } from '@/lib/dataforseo';

interface SEOBacklinksTabProps {
    brandId?: string | null;
    brandName?: string;
    brandUrl?: string;
}

interface CompetitorWithUrl {
    name: string;
    url: string;
}

function BacklinkDomainGroup({ domain, backlinks }: { domain: string, backlinks: any[] }) {
    const [isOpen, setIsOpen] = useState(false);
    const mainBacklink = backlinks[0];
    const isMulti = backlinks.length > 1;
    const dr = Math.round((mainBacklink.domainFromRank || 0) / 10);

    return (
        <div className="bg-white rounded-xl border border-slate-200 transition-all duration-200 hover:shadow-md hover:border-indigo-200 overflow-hidden">
            <div
                className="flex items-center justify-between p-4 cursor-pointer hover:bg-slate-50 transition-colors select-none"
                onClick={() => setIsOpen(!isOpen)}
            >
                <div className="flex items-center gap-3">
                    <div className={`p-1.5 rounded-lg transition-colors ${isOpen ? 'bg-indigo-100/50' : 'bg-slate-100'}`}>
                        <ChevronDown className={`w-4 h-4 text-slate-500 transition-transform duration-200 ${isOpen ? 'rotate-180 text-indigo-600' : ''}`} />
                    </div>
                    <div className="flex items-center gap-2">
                        {mainBacklink.domainFromCountry && (
                            <span className="text-lg leading-none" title={`Country: ${mainBacklink.domainFromCountry}`}>
                                {mainBacklink.domainFromCountry === 'US' ? '🇺🇸' : mainBacklink.domainFromCountry === 'GB' ? '🇬🇧' : mainBacklink.domainFromCountry}
                            </span>
                        )}
                        <span className="text-base font-bold text-slate-900">{domain}</span>
                        {mainBacklink.domainFromPlatformType && mainBacklink.domainFromPlatformType.length > 0 && (
                            <Badge variant="secondary" className="hidden sm:inline-flex text-[10px] h-5 bg-slate-100 text-slate-500 border-slate-200 border px-1.5 capitalize">
                                {mainBacklink.domainFromPlatformType[0]}
                            </Badge>
                        )}
                        {isMulti && (
                            <Badge variant="secondary" className="text-[10px] px-1.5 h-5 bg-slate-100 text-slate-600 border-slate-200 border">
                                {backlinks.length} Links
                            </Badge>
                        )}
                    </div>
                </div>

                <div className="flex items-center gap-2">
                    <Badge
                        className={`text-[10px] font-bold px-2 py-0.5 border ${dr >= 70 ? 'bg-purple-50 text-purple-700 border-purple-200' :
                            dr >= 50 ? 'bg-blue-50 text-blue-700 border-blue-200' :
                                dr >= 30 ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                                    'bg-slate-50 text-slate-600 border-slate-200'
                            }`}
                        variant="outline"
                    >
                        DR: {dr}
                    </Badge>
                </div>
            </div>

            {isOpen && (
                <div className="border-t border-slate-100 p-4 pt-2 bg-slate-50/30 space-y-3 animate-in slide-in-from-top-1 duration-200">
                    {backlinks.map((backlink: any, idx: number) => {
                        const ur = Math.round((backlink.pageFromRank || 0) / 10);
                        return (
                            <div key={idx} className="flex flex-col gap-2">
                                <div className="flex items-start justify-between gap-4">
                                    <div className="space-y-1.5 min-w-0 flex-1">
                                        {backlink.pageFromTitle && (
                                            <div className="flex items-start gap-2 mb-0.5">
                                                <span className="text-slate-400 text-[10px] uppercase tracking-wider font-medium mt-0.5 w-12 flex-shrink-0">Title:</span>
                                                <span className="text-xs text-slate-800 font-semibold truncate" title={backlink.pageFromTitle}>{backlink.pageFromTitle}</span>
                                            </div>
                                        )}

                                        {backlink.anchor && (
                                            <div className="flex items-start gap-2">
                                                <span className="text-slate-400 text-[10px] uppercase tracking-wider font-medium mt-0.5 w-12 flex-shrink-0">Anchor:</span>
                                                <span className="font-mono text-xs bg-slate-50 text-slate-700 px-1.5 py-0.5 rounded break-all border border-slate-100">{backlink.anchor}</span>
                                            </div>
                                        )}

                                        {(backlink.textPre || backlink.textPost) && (
                                            <div className="mt-2 text-[11px] text-slate-500 italic bg-white p-2 rounded border border-slate-100 leading-relaxed shadow-sm">
                                                "...{backlink.textPre} <span className="font-semibold text-indigo-600 not-italic bg-indigo-50 px-1 rounded">{backlink.anchor}</span> {backlink.textPost}..."
                                            </div>
                                        )}

                                        <div className="flex items-start gap-2 mt-1">
                                            <span className="text-slate-400 text-[10px] uppercase tracking-wider font-medium mt-0.5 w-12 flex-shrink-0">Source:</span>
                                            <a
                                                href={backlink.urlFrom}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="text-xs text-slate-500 hover:text-indigo-600 truncate break-all hover:underline"
                                            >
                                                {backlink.urlFrom}
                                            </a>
                                        </div>
                                    </div>

                                    <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
                                        <div className="flex gap-1.5">
                                            {backlink.dofollow ? (
                                                <Badge variant="outline" className="text-[10px] bg-green-50 text-green-700 border-green-200 font-semibold px-1.5 h-5">DoFollow</Badge>
                                            ) : (
                                                <Badge variant="outline" className="text-[10px] bg-slate-50 text-slate-600 border-slate-200 font-medium px-1.5 h-5">NoFollow</Badge>
                                            )}
                                            {backlink.isBroken && <Badge variant="destructive" className="text-[10px] px-1.5 h-5">Broken</Badge>}
                                            {backlink.backlinkSpamScore > 0 && (
                                                <Badge variant="outline" className={`text-[10px] px-1.5 h-5 font-bold border ${backlink.backlinkSpamScore > 50 ? 'bg-red-50 text-red-700 border-red-200' : 'bg-orange-50 text-orange-700 border-orange-200'}`}>
                                                    Spam: {backlink.backlinkSpamScore}
                                                </Badge>
                                            )}
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <span className="text-[10px] text-slate-400">
                                                UR: {ur}
                                            </span>
                                            <span className="text-[10px] text-slate-300">•</span>
                                            <span className="text-[10px] text-slate-400">
                                                {new Date(backlink.firstSeen).toLocaleDateString()}
                                            </span>
                                            {backlink.semanticLocation && (
                                                <>
                                                    <span className="text-[10px] text-slate-300">•</span>
                                                    <Badge variant="secondary" className="text-[9px] h-4 px-1 bg-violet-50 text-violet-700 border-violet-100 hover:bg-violet-100 capitalize border">
                                                        {backlink.semanticLocation}
                                                    </Badge>
                                                </>
                                            )}
                                            {backlink.itemType && (
                                                <>
                                                    <span className="text-[10px] text-slate-300">•</span>
                                                    <span className="text-[10px] text-slate-500 font-medium uppercase">
                                                        {backlink.itemType}
                                                    </span>
                                                </>
                                            )}
                                        </div>
                                    </div>
                                </div>
                                {idx < backlinks.length - 1 && <div className="border-b border-slate-100" />}
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}

export function SEOBacklinksTab({ brandId, brandName, brandUrl }: SEOBacklinksTabProps) {
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [data, setData] = useState<{
        brandName: string;
        brandUrl: string;
        competitorsCount: number;
        results: CompetitorBacklinkData[];
    } | null>(null);
    const [expandedCompetitors, setExpandedCompetitors] = useState<Set<string>>(new Set());

    // History state
    const [historyData, setHistoryData] = useState<any[]>([]);
    const [loadingHistory, setLoadingHistory] = useState(false);

    // Modal state
    const [showUrlModal, setShowUrlModal] = useState(false);
    const [editableCompetitors, setEditableCompetitors] = useState<CompetitorWithUrl[]>([]);

    // Backlinks detail state
    const [loadingBacklinks, setLoadingBacklinks] = useState<string | null>(null);
    const [competitorBacklinks, setCompetitorBacklinks] = useState<Record<string, any[]>>({});

    // Show modal with empty competitors to add
    const openCompetitorModal = () => {
        // Start with 1 empty slot
        setEditableCompetitors([
            { name: '', url: '' },
        ]);
        setShowUrlModal(true);
    };

    const handleCompetitorChange = (index: number, field: 'name' | 'url', value: string) => {
        setEditableCompetitors(prev => {
            const updated = [...prev];
            updated[index] = { ...updated[index], [field]: value };
            return updated;
        });
    };

    const addCompetitorSlot = () => {
        setEditableCompetitors(prev => [...prev, { name: '', url: '' }]);
    };

    const removeCompetitorSlot = (index: number) => {
        setEditableCompetitors(prev => prev.filter((_, i) => i !== index));
    };

    // Load history on mount or when brandId changes
    useEffect(() => {
        if (brandId) {
            fetchHistory();
        }
    }, [brandId]);

    // Fetch backlinks history and auto-load all competitors
    const fetchHistory = async () => {
        if (!brandId) return;

        setLoadingHistory(true);
        try {
            const response = await fetch(`/api/backlinks/history?brandId=${brandId}`);
            const result = await response.json();

            if (response.ok && result.analyses) {
                setHistoryData(result.analyses);

                // Merge all unique competitors from all analyses
                if (result.analyses.length > 0) {
                    const allCompetitors = new Map<string, any>();

                    // Iterate through all analyses, newest first
                    result.analyses.forEach((analysis: any) => {
                        analysis.analysisResults.forEach((competitor: any) => {
                            // Use URL as unique key, keep the most recent data (first occurrence)
                            if (!allCompetitors.has(competitor.url)) {
                                allCompetitors.set(competitor.url, {
                                    ...competitor,
                                    analysisId: analysis.id, // Track which analysis this came from
                                    analysisDate: analysis.createdAt,
                                });
                            } else {
                                // If competitor exists, merge backlinks if the new one has them
                                const existing = allCompetitors.get(competitor.url);
                                if (competitor.backlinks?.length > 0 && !existing.backlinks?.length) {
                                    allCompetitors.set(competitor.url, {
                                        ...existing,
                                        backlinks: competitor.backlinks,
                                        analysisId: analysis.id, // Update to the analysis that has backlinks
                                    });
                                }
                            }
                        });
                    });

                    // Convert map to array and set as data
                    const mergedCompetitors = Array.from(allCompetitors.values());

                    setData({
                        brandName: result.analyses[0].brandName,
                        brandUrl: result.analyses[0].brandUrl,
                        competitorsCount: mergedCompetitors.length,
                        results: mergedCompetitors,
                    });

                    console.log(`[SEO Backlinks] Loaded ${mergedCompetitors.length} unique competitors from ${result.analyses.length} analyses`);
                } else {
                    // No history found, set empty state
                    setData({
                        brandName: brandName || '',
                        brandUrl: brandUrl || '',
                        competitorsCount: 0,
                        results: [],
                    });
                }
            }
        } catch (err) {
            console.error('Failed to fetch history:', err);
        } finally {
            setLoadingHistory(false);
        }
    };



    // Fetch detailed backlinks for a specific competitor
    const fetchCompetitorBacklinks = async (competitorUrl: string, competitorName: string) => {
        if (competitorBacklinks[competitorUrl]) {
            // Already loaded in state, just toggle
            return;
        }

        // Check if backlinks already exist in the loaded data (from history)
        if (data?.results) {
            const competitor = data.results.find(r => r.url === competitorUrl);
            if (competitor?.backlinks && competitor.backlinks.length > 0) {
                console.log('[SEO Backlinks] Using cached backlinks from history', {
                    backlinksCount: competitor.backlinks.length,
                });
                setCompetitorBacklinks(prev => ({
                    ...prev,
                    [competitorUrl]: competitor.backlinks,
                }));
                return;
            }
        }

        // No cached data, fetch from API
        console.log('[SEO Backlinks] Fetching fresh backlinks for competitor');
        setLoadingBacklinks(competitorUrl);

        try {
            const response = await fetch('/api/backlinks/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    brandId,
                    includeSummary: false,
                    includeBacklinks: true,
                    backlinksLimit: 100,
                    competitors: [{ name: competitorName, url: competitorUrl }],
                }),
            });

            const result = await response.json();

            if (response.ok && result.results?.[0]?.backlinks) {
                const fetchedBacklinks = result.results[0].backlinks;

                setCompetitorBacklinks(prev => ({
                    ...prev,
                    [competitorUrl]: fetchedBacklinks,
                }));

                // Save to database if this competitor came from a history record
                const competitor = data?.results.find(r => r.url === competitorUrl);
                if (competitor?.analysisId) {
                    try {
                        await fetch('/api/backlinks/update-competitor', {
                            method: 'PATCH',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                analysisId: competitor.analysisId,
                                competitorUrl,
                                backlinks: fetchedBacklinks,
                            }),
                        });
                        console.log('[SEO Backlinks] Saved backlinks to database for future use');

                        // Update the local data state to include the backlinks
                        setData(prev => {
                            if (!prev) return prev;
                            return {
                                ...prev,
                                results: prev.results.map(r =>
                                    r.url === competitorUrl
                                        ? { ...r, backlinks: fetchedBacklinks }
                                        : r
                                ),
                            };
                        });
                    } catch (saveError) {
                        console.error('[SEO Backlinks] Failed to save backlinks to database:', saveError);
                        // Don't fail the UI if save fails
                    }
                }
            }
        } catch (err) {
            console.error('Failed to fetch backlinks:', err);
        } finally {
            setLoadingBacklinks(null);
        }
    };

    const analyzeWithUrls = async () => {
        setShowUrlModal(false);
        setIsLoading(true);
        setError(null);

        try {
            console.log('[SEO Backlinks] Analyzing custom competitor list', {
                competitorCount: editableCompetitors.filter(c => c.name && c.url).length,
            });
            const response = await fetch('/api/backlinks/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    brandId,
                    includeSummary: true,
                    includeBacklinks: false,
                    competitors: editableCompetitors.filter(c => c.name && c.url), // Send only filled competitors
                }),
            });

            const result = await response.json();
            console.log('[SEO Backlinks] Analysis API call completed');

            if (!response.ok) {
                throw new Error(result.error || 'Failed to fetch backlinks data');
            }

            setData(result);
            // Refresh history after new analysis
            fetchHistory();
        } catch (err: any) {
            console.error('[SEO Backlinks] Error:', err);
            setError(err.message || 'Failed to analyze backlinks');
        } finally {
            setIsLoading(false);
        }
    };

    const toggleExpand = (competitorKey: string) => {
        if (!competitorKey) return;
        setExpandedCompetitors(prev => {
            const next = new Set(prev);
            if (next.has(competitorKey)) {
                next.delete(competitorKey);
            } else {
                next.add(competitorKey);
            }
            return next;
        });
    };

    const formatNumber = (num: number | undefined): string => {
        if (num === undefined || num === null) return '—';
        if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
        if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
        return num.toLocaleString();
    };

    const getDrColor = (dr: number): string => {
        if (dr >= 70) return 'text-purple-700 bg-purple-50 border-purple-200 border';
        if (dr >= 50) return 'text-blue-700 bg-blue-50 border-blue-200 border';
        if (dr >= 30) return 'text-emerald-700 bg-emerald-50 border-emerald-200 border';
        return 'text-slate-600 bg-slate-50 border-slate-200 border';
    };

    return (
        <div className="flex h-full relative flex-col">
            <div className="flex-1 overflow-y-auto">
                {/* Hero Header */}
                <div>
                    <div className="max-w-6xl mx-auto px-4 md:px-8 py-8">
                        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                            <div>

                                <h2 className="text-2xl md:text-3xl font-bold text-slate-900">Backlinks Analysis</h2>
                                <p className="text-slate-500 mt-2 max-w-lg">
                                    Discover where your competitors get their links. Find opportunities to build your own authority.
                                </p>
                            </div>
                            <div className="flex flex-col sm:flex-row gap-3">
                                <Button
                                    onClick={openCompetitorModal}
                                    disabled={isLoading}
                                    size="lg"
                                    className="gap-2 bg-slate-900 hover:bg-slate-800 text-white shadow-lg hover:shadow-xl transition-all"
                                >
                                    {isLoading ? (
                                        <>
                                            <Loader2 className="w-4 h-4 animate-spin" />
                                            Analyzing...
                                        </>
                                    ) : (
                                        <>
                                            <RefreshCw className="w-4 h-4" />
                                            New Analysis
                                        </>
                                    )}
                                </Button>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="max-w-6xl mx-auto px-4 md:px-8 py-8 space-y-8">

                    {/* URL Editing Modal */}
                    <Dialog open={showUrlModal} onOpenChange={setShowUrlModal}>
                        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
                            <DialogHeader>
                                <DialogTitle>Add Competitor URLs</DialogTitle>
                                <DialogDescription>
                                    Enter competitor names and their website URLs to analyze backlinks.
                                </DialogDescription>
                            </DialogHeader>

                            <div className="space-y-4 py-4">
                                {editableCompetitors.map((competitor, index) => (
                                    <div key={index} className="grid grid-cols-12 gap-2 items-end">
                                        <div className="col-span-5">
                                            <Label htmlFor={`name-${index}`} className="text-xs text-slate-500">
                                                Competitor Name
                                            </Label>
                                            <Input
                                                id={`name-${index}`}
                                                value={competitor.name}
                                                onChange={(e) => handleCompetitorChange(index, 'name', e.target.value)}
                                                placeholder="e.g., Competitor Inc"
                                                className="text-sm"
                                            />
                                        </div>
                                        <div className="col-span-6">
                                            <Label htmlFor={`url-${index}`} className="text-xs text-slate-500">
                                                Website URL
                                            </Label>
                                            <Input
                                                id={`url-${index}`}
                                                value={competitor.url}
                                                onChange={(e) => handleCompetitorChange(index, 'url', e.target.value)}
                                                placeholder="e.g., competitor.com"
                                                className="font-mono text-sm"
                                            />
                                        </div>
                                        <div className="col-span-1">
                                            {editableCompetitors.length > 1 && (
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => removeCompetitorSlot(index)}
                                                    className="h-9 w-9 p-0 text-red-500 hover:text-red-700 hover:bg-red-50"
                                                >
                                                    <X className="w-4 h-4" />
                                                </Button>
                                            )}
                                        </div>
                                    </div>
                                ))}

                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={addCompetitorSlot}
                                    className="w-full"
                                >
                                    + Add Another Competitor
                                </Button>
                            </div>

                            <DialogFooter>
                                <Button variant="outline" onClick={() => setShowUrlModal(false)}>
                                    Cancel
                                </Button>
                                <Button
                                    onClick={analyzeWithUrls}
                                    className="bg-indigo-600 hover:bg-indigo-700"
                                    disabled={editableCompetitors.filter(c => c.name && c.url).length === 0}
                                >
                                    <RefreshCw className="w-4 h-4 mr-2" />
                                    Analyze {editableCompetitors.filter(c => c.name && c.url).length} Competitors
                                </Button>
                            </DialogFooter>
                        </DialogContent>
                    </Dialog>

                    {/* Error State */}
                    {error && (
                        <Card className="border-red-200 bg-red-50">
                            <CardContent className="flex items-center gap-3 p-4">
                                <AlertCircle className="w-5 h-5 text-red-600" />
                                <p className="text-red-800">{error}</p>
                            </CardContent>
                        </Card>
                    )}

                    {/* Loading State */}
                    {isLoading && (
                        <div className="flex flex-col items-center justify-center py-20">
                            <Loader2 className="w-12 h-12 text-indigo-500 animate-spin mb-4" />
                            <p className="text-slate-600 font-medium">Analyzing backlink profile...</p>
                            <p className="text-slate-400 text-sm mt-1">This may take a moment for multiple competitors</p>
                        </div>
                    )}

                    {/* History Loading State */}
                    {loadingHistory && (
                        <div className="flex flex-col items-center justify-center py-20 min-h-[400px]">
                            <Loader2 className="w-12 h-12 text-indigo-500 animate-spin mb-4" />
                            <h3 className="text-xl font-semibold text-slate-900 mb-2">Loading History...</h3>
                            <p className="text-slate-500">Fetching your past backlink analyses</p>
                        </div>
                    )}

                    {/* Results */}
                    {data && !isLoading && !loadingHistory && (
                        <>
                            {/* Summary Stats */}
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <p className="text-sm text-slate-500 mb-1">Competitors</p>
                                            <p className="text-3xl font-semibold text-slate-900 tabular-nums">{data.competitorsCount}</p>
                                        </div>
                                        <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center">
                                            <Globe className="w-5 h-5 text-slate-600" />
                                        </div>
                                    </div>
                                </div>

                                <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <p className="text-sm text-slate-500 mb-1">Total Backlinks</p>
                                            <p className="text-3xl font-semibold text-slate-900 tabular-nums">
                                                {formatNumber(
                                                    data.results.reduce((sum, r) => sum + (r.summary?.backlinks || 0), 0)
                                                )}
                                            </p>
                                        </div>
                                        <div className="w-12 h-12 rounded-full bg-emerald-50 flex items-center justify-center">
                                            <LinkIcon className="w-5 h-5 text-emerald-600" />
                                        </div>
                                    </div>
                                </div>

                                <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <p className="text-sm text-slate-500 mb-1">Avg. Ref. Domains</p>
                                            <p className="text-3xl font-semibold text-slate-900 tabular-nums">
                                                {formatNumber(
                                                    Math.round(
                                                        data.results.reduce((sum, r) => sum + (r.summary?.referringDomains || 0), 0) /
                                                        Math.max(data.results.filter(r => r.summary).length, 1)
                                                    )
                                                )}
                                            </p>
                                        </div>
                                        <div className="w-12 h-12 rounded-full bg-violet-50 flex items-center justify-center">
                                            <TrendingUp className="w-5 h-5 text-violet-600" />
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Competitor Results */}
                            <div className="space-y-4 mt-8">
                                <div className="flex items-center justify-between">
                                    <h3 className="text-base font-medium text-slate-700">Competitor Profiles</h3>
                                    <span className="text-xs text-slate-400">{data.results.length} analyzed</span>
                                </div>

                                {data.results.map((result) => {
                                    const competitorKey = result.url || result.competitor;
                                    return (
                                        <div
                                            key={competitorKey}
                                            className={`bg-white rounded-xl border transition-all duration-150 ${expandedCompetitors.has(competitorKey) ? 'border-slate-300 shadow-md' : 'border-slate-200 hover:border-slate-300'}`}
                                        >
                                            <div
                                                className="flex items-center justify-between p-5 cursor-pointer"
                                                onClick={() => toggleExpand(competitorKey)}
                                            >
                                                <div className="flex items-center gap-4 min-w-0">
                                                    <div className="w-10 h-10 rounded-lg bg-slate-100 flex items-center justify-center flex-shrink-0">
                                                        <span className="text-sm font-bold text-slate-600">{result.competitor.charAt(0).toUpperCase()}</span>
                                                    </div>
                                                    <div className="min-w-0">
                                                        <p className="font-semibold text-slate-900 truncate">{result.competitor}</p>
                                                        <a
                                                            href={result.url.startsWith('http') ? result.url : `https://${result.url}`}
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                            className="text-sm text-slate-400 hover:text-indigo-600 truncate block"
                                                            onClick={(e) => e.stopPropagation()}
                                                        >
                                                            {result.url}
                                                        </a>
                                                    </div>
                                                </div>

                                                <div className="flex items-center gap-4 md:gap-6 flex-shrink-0">
                                                    {result.error ? (
                                                        <span className="text-xs text-red-500 font-medium">Error</span>
                                                    ) : result.summary ? (
                                                        <>
                                                            <div className="text-right hidden sm:block">
                                                                <p className="text-xs text-slate-400">Backlinks</p>
                                                                <p className="text-lg font-semibold text-slate-900 tabular-nums">
                                                                    {formatNumber(result.summary.backlinks)}
                                                                </p>
                                                            </div>
                                                            <div className="text-right hidden md:block">
                                                                <p className="text-xs text-slate-400">Ref. Domains</p>
                                                                <p className="text-lg font-semibold text-slate-900 tabular-nums">
                                                                    {formatNumber(result.summary.referringDomains)}
                                                                </p>
                                                            </div>
                                                        </>
                                                    ) : (
                                                        <span className="text-xs text-slate-400">No data</span>
                                                    )}
                                                    <ChevronDown className={`w-5 h-5 text-slate-400 transition-transform duration-200 ${expandedCompetitors.has(competitorKey) ? 'rotate-180' : ''}`} />
                                                </div>
                                            </div>

                                            {/* Expanded Details */}
                                            {expandedCompetitors.has(competitorKey) && result.summary && (
                                                <CardContent className="border-t border-slate-100 bg-slate-50/50 p-6">
                                                <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                                                    <div className="space-y-1 p-4 bg-white rounded-xl border border-slate-100 shadow-sm">
                                                        <p className="text-xs text-purple-600 font-medium uppercase tracking-wider">Domain Rating</p>
                                                        <p className="text-2xl font-bold text-purple-900 tracking-tight">{Math.round((result.summary?.rank || 0) / 10)}</p>
                                                    </div>
                                                    <div className="space-y-1 p-4 bg-white rounded-xl border border-slate-100 shadow-sm">
                                                        <p className="text-xs text-red-600 font-medium uppercase tracking-wider">Target Spam Score</p>
                                                        <p className="text-2xl font-bold text-red-900 tracking-tight">{result.summary?.info?.targetSpamScore || 0}</p>
                                                    </div>
                                                    <div className="space-y-1 p-4 bg-white rounded-xl border border-slate-100 shadow-sm">
                                                        <p className="text-xs text-slate-500 font-medium uppercase tracking-wider">Total Backlinks</p>
                                                        <p className="text-2xl font-bold text-slate-900 tracking-tight">{formatNumber(result.summary.backlinks)}</p>
                                                    </div>
                                                    <div className="space-y-1 p-4 bg-white rounded-xl border border-slate-100 shadow-sm">
                                                        <p className="text-xs text-emerald-600 font-medium uppercase tracking-wider">Referring Domains</p>
                                                        <p className="text-2xl font-bold text-emerald-900 tracking-tight">{formatNumber(result.summary.referringDomains)}</p>
                                                    </div>
                                                    <div className="space-y-1 p-4 bg-white rounded-xl border border-slate-100 shadow-sm">
                                                        <p className="text-xs text-slate-500 font-medium uppercase tracking-wider">Main Domains</p>
                                                        <p className="text-2xl font-bold text-slate-900 tracking-tight">{formatNumber(result.summary.referringMainDomains)}</p>
                                                    </div>
                                                    <div className="space-y-1 p-4 bg-white rounded-xl border border-slate-100 shadow-sm">
                                                        <p className="text-xs text-slate-500 font-medium uppercase tracking-wider">Referring IPs</p>
                                                        <p className="text-2xl font-bold text-slate-900 tracking-tight">{formatNumber(result.summary.referringIps)}</p>
                                                    </div>
                                                    <div className="space-y-1 p-4 bg-white rounded-xl border border-slate-100 shadow-sm">
                                                        <p className="text-xs text-amber-600 font-medium uppercase tracking-wider">Nofollow Domains</p>
                                                        <p className="text-2xl font-bold text-amber-900 tracking-tight">{formatNumber(result.summary.referringDomainsNofollow)}</p>
                                                    </div>
                                                    <div className="space-y-1 p-4 bg-white rounded-xl border border-slate-100 shadow-sm">
                                                        <p className="text-xs text-red-600 font-medium uppercase tracking-wider">Broken Backlinks</p>
                                                        <p className="text-2xl font-bold text-red-900 tracking-tight">{formatNumber(result.summary.brokenBacklinks)}</p>
                                                    </div>
                                                    <div className="space-y-1 p-4 bg-white rounded-xl border border-slate-100 shadow-sm">
                                                        <p className="text-xs text-purple-600 font-medium uppercase tracking-wider">Detailed Spam Score</p>
                                                        <p className="text-2xl font-bold text-purple-900 tracking-tight">
                                                            {result.summary.backlinksSpamScore?.toFixed(0) || '—'}%
                                                        </p>
                                                    </div>
                                                    <div className="space-y-1 p-4 bg-white rounded-xl border border-slate-100 shadow-sm">
                                                        <p className="text-xs text-blue-600 font-medium uppercase tracking-wider">External Links</p>
                                                        <p className="text-2xl font-bold text-blue-900 tracking-tight">{formatNumber(result.summary.externalLinksCount)}</p>
                                                    </div>
                                                </div>

                                                {/* TLD Distribution */}
                                                {result.summary.referringLinksTld && Object.keys(result.summary.referringLinksTld).length > 0 && (
                                                    <div className="mb-6">
                                                        <p className="text-xs text-slate-500 uppercase tracking-wider font-semibold mb-3">Top TLDs</p>
                                                        <div className="flex flex-wrap gap-2">
                                                            {Object.entries(result.summary.referringLinksTld)
                                                                .sort(([, a], [, b]) => b - a)
                                                                .slice(0, 8)
                                                                .map(([tld, count]) => (
                                                                    <Badge key={tld} variant="secondary" className="text-xs bg-slate-100 text-slate-600 hover:bg-slate-200 border-slate-200">
                                                                        .{tld} <span className="ml-1.5 opacity-60">|</span> <span className="ml-1.5 font-bold">{formatNumber(count)}</span>
                                                                    </Badge>
                                                                ))}
                                                        </div>
                                                    </div>
                                                )}

                                                {/* View Backlinks Button */}
                                                <div className="mt-8 pt-6 border-t border-slate-200">
                                                    <Button
                                                        onClick={() => fetchCompetitorBacklinks(result.url, result.competitor)}
                                                        disabled={loadingBacklinks === result.url}
                                                        className={`w-full py-6 text-sm font-medium transition-all ${competitorBacklinks[result.url] ? 'bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-200' : 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-md hover:shadow-lg'}`}
                                                    >
                                                        {loadingBacklinks === result.url ? (
                                                            <>
                                                                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                                                Loading Top 100 Backlinks...
                                                            </>
                                                        ) : competitorBacklinks[result.url] ? (
                                                            <>
                                                                <RefreshCw className="w-4 h-4 mr-2" />
                                                                Refresh Backlinks (Showing {competitorBacklinks[result.url].length})
                                                            </>
                                                        ) : (
                                                            <>
                                                                <LinkIcon className="w-4 h-4 mr-2" />
                                                                View Top 100 Backlinks
                                                            </>
                                                        )}
                                                    </Button>
                                                </div>

                                                {/* Backlinks List */}
                                                {competitorBacklinks[result.url] && (
                                                    <div className="mt-6 animate-in slide-in-from-top-2 duration-300">
                                                        {/* Quick Stats Grid */}
                                                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                                                            <div className="bg-green-50/50 border border-green-100 rounded-lg p-3 text-center">
                                                                <p className="text-[10px] uppercase tracking-wider text-green-600 font-bold mb-1">DoFollow</p>
                                                                <p className="text-xl font-bold text-green-700">
                                                                    {competitorBacklinks[result.url].filter((b: any) => b.dofollow).length}
                                                                </p>
                                                            </div>
                                                            <div className="bg-amber-50/50 border border-amber-100 rounded-lg p-3 text-center">
                                                                <p className="text-[10px] uppercase tracking-wider text-amber-600 font-bold mb-1">NoFollow</p>
                                                                <p className="text-xl font-bold text-amber-700">
                                                                    {competitorBacklinks[result.url].filter((b: any) => !b.dofollow).length}
                                                                </p>
                                                            </div>
                                                            <div className="bg-red-50/50 border border-red-100 rounded-lg p-3 text-center">
                                                                <p className="text-[10px] uppercase tracking-wider text-red-600 font-bold mb-1">Broken</p>
                                                                <p className="text-xl font-bold text-red-700">
                                                                    {competitorBacklinks[result.url].filter((b: any) => b.isBroken).length}
                                                                </p>
                                                            </div>
                                                            <div className="bg-purple-50/50 border border-purple-100 rounded-lg p-3 text-center">
                                                                <p className="text-[10px] uppercase tracking-wider text-purple-600 font-bold mb-1">Avg Spam</p>
                                                                <p className="text-xl font-bold text-purple-700">
                                                                    {(competitorBacklinks[result.url].reduce((sum: number, b: any) => sum + (b.backlinkSpamScore || 0), 0) / competitorBacklinks[result.url].length).toFixed(0)}%
                                                                </p>
                                                            </div>
                                                        </div>

                                                        <div className="flex items-center justify-between mb-3 px-1">
                                                            <p className="text-sm font-semibold text-slate-800">
                                                                Link Opportunities
                                                            </p>
                                                            <span className="text-xs text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full">Sorted by DR</span>
                                                        </div>

                                                        <div className="max-h-[600px] overflow-y-auto space-y-3 pr-2 scrollbar-thin scrollbar-thumb-slate-200 scrollbar-track-transparent">
                                                            {Object.entries(competitorBacklinks[result.url].reduce((acc: any, backlink: any) => {
                                                                const domain = backlink.domainFrom || 'Unknown Domain';
                                                                if (!acc[domain]) acc[domain] = [];
                                                                acc[domain].push(backlink);
                                                                return acc;
                                                            }, {}) as Record<string, any[]>)
                                                                .sort(([, a], [, b]) => {
                                                                    const daA = a[0]?.domainFromRank || 0;
                                                                    const daB = b[0]?.domainFromRank || 0;
                                                                    return daB - daA;
                                                                })
                                                                .map(([domain, backlinks], groupIdx) => (
                                                                    <BacklinkDomainGroup
                                                                        key={groupIdx}
                                                                        domain={domain}
                                                                        backlinks={backlinks}
                                                                    />
                                                                ))}
                                                        </div>

                                                        {/* Modern Legend */}
                                                        <div className="mt-4 flex flex-wrap gap-4 text-xs text-slate-500 bg-slate-50 rounded-lg p-3 border border-slate-100">
                                                            <div className="flex items-center gap-1.5">
                                                                <span className="w-2 h-2 rounded-full bg-green-500"></span>
                                                                <span className="font-medium">High DR (50+)</span>
                                                            </div>
                                                            <div className="flex items-center gap-1.5">
                                                                <span className="w-2 h-2 rounded-full bg-purple-500"></span>
                                                                <span className="font-medium">Premium DR (70+)</span>
                                                            </div>
                                                            <div className="flex items-center gap-1.5">
                                                                <span className="w-2 h-2 rounded-full bg-red-500"></span>
                                                                <span className="font-medium">Broken/High Spam</span>
                                                            </div>
                                                            <div className="flex items-center gap-1.5 ml-auto">
                                                                <span className="font-medium text-indigo-600">💡 Pro Tip:</span>
                                                                <span>Target broken high-DR links first.</span>
                                                            </div>
                                                        </div>
                                                    </div>
                                                )}
                                            </CardContent>
                                        )}

                                        {/* Error Message */}
                                        {expandedCompetitors.has(competitorKey) && result.error && (
                                            <CardContent className="pt-0 border-t">
                                                <div className="flex items-center gap-2 text-red-600 py-4">
                                                    <AlertCircle className="w-4 h-4" />
                                                    <p className="text-sm">{result.error}</p>
                                                </div>
                                            </CardContent>
                                        )}
                                        </div>
                                    );
                                })}
                            </div>
                        </>
                    )}

                    {/* Empty State - After fetch with no data */}
                    {data && data.results.length === 0 && !isLoading && (
                        <Card className="border-slate-200">
                            <CardContent className="flex flex-col items-center justify-center py-12">
                                <LinkIcon className="w-12 h-12 text-slate-300 mb-4" />
                                <h3 className="text-lg font-medium text-slate-700 mb-2">No Competitors Found</h3>
                                <p className="text-slate-500 text-center max-w-md">
                                    No competitors were analyzed. Please try again with valid competitor URLs.
                                </p>
                            </CardContent>
                        </Card>
                    )}

                </div>
            </div>
        </div>
    );
}

export default SEOBacklinksTab;
