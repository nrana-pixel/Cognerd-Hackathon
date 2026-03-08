import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@/lib/auth';
import { headers } from 'next/headers';
import { getDb } from '@/lib/mongo';
import { randomUUID } from 'crypto';

/**
 * GET /api/backlinks/history
 * 
 * Fetches backlinks analysis history for a specific brand
 * 
 * Query params:
 * - brandId: string - The brand profile ID
 */
export async function GET(request: NextRequest) {
  try {
    // Authenticate
    const session = await auth.api.getSession({ headers: await headers() });
    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { searchParams } = new URL(request.url);
    const brandId = searchParams.get('brandId');

    if (!brandId) {
      return NextResponse.json({ error: 'brandId is required' }, { status: 400 });
    }

    // Fetch all analyses for this brand and user from MongoDB
    const db = await getDb();
    const collection = db.collection('backlink_analyses');
    
    const analyses = await collection
      .find({
        brandId,
        userId: session.user.id,
      })
      .sort({ createdAt: -1 })
      .toArray();

    // Convert MongoDB _id to string id for frontend compatibility
    // Also ensure analysisResults are properly serialized
    const formattedAnalyses = analyses.map(analysis => {
      const { _id, ...rest } = analysis;
      return {
        ...rest,
        id: _id.toString(),
        // Ensure analysisResults is properly formatted as a plain array
        analysisResults: Array.isArray(analysis.analysisResults) 
          ? analysis.analysisResults.map((result: any) => {
              // Remove any MongoDB-specific fields from nested objects
              const { _id: resultId, ...resultData } = result;
              return resultData;
            })
          : [],
      };
    });

    return NextResponse.json({
      success: true,
      analyses: formattedAnalyses,
    });

  } catch (error: any) {
    const errorId = randomUUID();
    console.error('Backlinks history error:', errorId, error);
    return NextResponse.json({ 
      error: 'Failed to fetch backlinks history. Please try again later.',
      errorId,
    }, { status: 500 });
  }
}
