import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@/lib/auth';
import { headers } from 'next/headers';
import { db } from '@/lib/db';
import { randomUUID } from 'crypto';
import { brandprofile } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';
import { getDataForSEOClient, type CompetitorBacklinkData } from '@/lib/dataforseo';

/**
 * POST /api/backlinks/analyze
 * 
 * Fetches backlink data for competitors of a brand profile
 * 
 * Request body:
 * - brandId: string - The brand profile ID to get competitors from
 * - includeSummary?: boolean - Include summary stats (default: true)
 * - includeBacklinks?: boolean - Include detailed backlinks list (default: false)
 * - backlinksLimit?: number - Max backlinks per competitor (default: 50)
 */
export async function POST(request: NextRequest) {
  try {
    // Authenticate
    const session = await auth.api.getSession({ headers: await headers() });
    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body = await request.json();
    const { brandId, includeSummary = true, includeBacklinks = false, backlinksLimit = 50, competitors: providedCompetitors } = body;

    if (!brandId) {
      return NextResponse.json({ error: 'brandId is required' }, { status: 400 });
    }

    // Fetch brand profile
    const brandProfile = await db.query.brandprofile.findFirst({
      where: eq(brandprofile.id, brandId),
    });

    if (!brandProfile) {
      return NextResponse.json({ error: 'Brand profile not found' }, { status: 404 });
    }

    // Check user owns this brand profile (or is superuser)
    const superuserEmails = (process.env.SUPERUSER_EMAILS || '').split(',').map(e => e.trim().toLowerCase());
    const isSuperuser = superuserEmails.includes(session.user.email?.toLowerCase() || '');
    
    if (brandProfile.userId !== session.user.id && !isSuperuser) {
      return NextResponse.json({ error: 'Forbidden' }, { status: 403 });
    }

    let competitors: Array<{ name: string; url: string }> = [];

    // If competitors are provided in the request, use them directly
    if (providedCompetitors && Array.isArray(providedCompetitors) && providedCompetitors.length > 0) {
      competitors = providedCompetitors.filter((c: any) => c.name && c.url);
      console.log('[Backlinks API] Using provided competitors list', {
        competitorCount: competitors.length,
      });
    } else {
      // Otherwise, extract from database
      // Helper function to generate a likely domain from company name
      const generateDomainFromName = (name: string): string => {
        // Remove common suffixes and clean the name
        const cleaned = name
          .toLowerCase()
          .replace(/\s+(inc|llc|ltd|limited|technologies|tech|pvt|private)\b/gi, '')
          .replace(/[^a-z0-9]/g, '')
          .trim();
        
        return cleaned ? `${cleaned}.com` : '';
      };

      // Helper to check if a string looks like a URL
      const looksLikeUrl = (str: string): boolean => {
        return str.includes('.') || str.startsWith('http');
      };

      // Extract competitors from brand profile
      if (brandProfile.competitors) {
        const rawCompetitors = brandProfile.competitors as any;
        
        if (Array.isArray(rawCompetitors)) {
          competitors = rawCompetitors
            .map((c: any) => {
              if (typeof c === 'string') {
                // Plain string - check if it's a URL or just a name
                const url = looksLikeUrl(c) ? c : generateDomainFromName(c);
                return { name: c, url };
              } else if (c && typeof c === 'object') {
                const name = c.name || c.companyName || c.title || c.url || '';
                let url = c.url || c.website || c.domain || '';
                
                // If no URL, try to generate one from the name
                if (!url && name) {
                  url = generateDomainFromName(name);
                }
                
                return { name, url };
              }
              return null;
            })
            .filter((c: any): c is { name: string; url: string } => c !== null && c.url !== '');
        }
      }

      // Also check scrapedData for competitors
      if (competitors.length === 0 && brandProfile.scrapedData) {
        const scrapedData = brandProfile.scrapedData as any;
        
        if (scrapedData.competitors && Array.isArray(scrapedData.competitors)) {
          competitors = scrapedData.competitors
            .map((c: any) => {
              if (typeof c === 'string') {
                const url = looksLikeUrl(c) ? c : generateDomainFromName(c);
                return { name: c, url };
              } else if (c && typeof c === 'object') {
                const name = c.name || c.companyName || c.url || '';
                let url = c.url || c.website || '';
                
                if (!url && name) {
                  url = generateDomainFromName(name);
                }
                
                return { name, url };
              }
              return null;
            })
            .filter((c: any): c is { name: string; url: string } => c !== null && c.url !== '');
        }
        
        // Also try competitorDetails
        if (competitors.length === 0 && scrapedData.competitorDetails && Array.isArray(scrapedData.competitorDetails)) {
          competitors = scrapedData.competitorDetails
            .map((c: any) => {
              const name = c.name || '';
              let url = c.url || '';
              
              if (!url && name) {
                url = generateDomainFromName(name);
              }
              
              return { name, url };
            })
            .filter((c: any) => c.url !== '');
        }
      }
    }

    if (competitors.length === 0) {
      return NextResponse.json({ 
        error: 'No competitors found for this brand profile',
        brandId,
        brandName: brandProfile.name,
      }, { status: 400 });
    }

    // Initialize DataForSEO client and fetch backlink data
    const client = getDataForSEOClient();
    const results: CompetitorBacklinkData[] = await client.getCompetitorsBacklinks(
      competitors,
      { includeSummary, includeBacklinks, backlinksLimit }
    );

    // Save analysis to MongoDB for history (only for full analyses with summary data)
    if (includeSummary) {
      try {
        const { getDb } = await import('@/lib/mongo');
        const db = await getDb();
        const collection = db.collection('backlink_analyses');
        
        // Calculate totals
        const totalBacklinks = results.reduce((sum, r) => sum + (r.summary?.backlinks || 0), 0);
        const totalReferringDomains = results.reduce((sum, r) => sum + (r.summary?.referringDomains || 0), 0);

        // Always create a new analysis record (snapshot)
        await collection.insertOne({
          userId: session.user.id,
          brandId,
          brandName: brandProfile.name,
          brandUrl: brandProfile.url,
          analysisResults: results,
          competitorsCount: results.length,
          totalBacklinks,
          totalReferringDomains,
          createdAt: new Date(),
          updatedAt: new Date(),
        });

        console.log('[Backlinks] Saved analysis snapshot', {
          brandId,
          competitorsCount: results.length,
        });
      } catch (dbError) {
        console.error('Failed to save backlinks analysis to MongoDB:', dbError);
        // Don't fail the request if DB save fails
      }
    }

    return NextResponse.json({
      success: true,
      brandId,
      brandName: brandProfile.name,
      brandUrl: brandProfile.url,
      competitorsCount: competitors.length,
      results,
    });

  } catch (error: any) {
    const errorId = randomUUID();
    console.error('Backlinks analyze error:', errorId, error);
    
    // Handle specific errors
    if (error.message?.includes('credentials not configured')) {
      return NextResponse.json({ 
        error: 'DataForSEO API not configured. Please contact support.',
        errorId,
      }, { status: 503 });
    }

    return NextResponse.json({ 
      error: 'Failed to analyze backlinks. Please try again later.',
      errorId,
    }, { status: 500 });
  }
}
