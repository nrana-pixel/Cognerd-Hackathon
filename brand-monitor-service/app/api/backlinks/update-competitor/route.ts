import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@/lib/auth';
import { headers } from 'next/headers';
import { getDb } from '@/lib/mongo';
import { ObjectId } from 'mongodb';
import { randomUUID, createHash } from 'crypto';

/**
 * PATCH /api/backlinks/update-competitor
 * 
 * Updates a specific competitor's backlinks in an existing analysis
 * Used when fetching detailed backlinks for a competitor from history
 * 
 * Request body:
 * - analysisId: string - The analysis record ID
 * - competitorUrl: string - The competitor URL to update
 * - backlinks: Backlink[] - The backlinks data to save
 */
export async function PATCH(request: NextRequest) {
  try {
    // Authenticate
    const session = await auth.api.getSession({ headers: await headers() });
    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body = await request.json();
    const { analysisId, competitorUrl, backlinks } = body;

    if (!analysisId || !competitorUrl || !backlinks) {
      return NextResponse.json({ 
        error: 'analysisId, competitorUrl, and backlinks are required' 
      }, { status: 400 });
    }

    if (!ObjectId.isValid(analysisId)) {
      return NextResponse.json({
        error: 'Invalid analysisId format',
      }, { status: 400 });
    }

    const analysisObjectId = new ObjectId(analysisId);

    // Update the specific competitor's backlinks in MongoDB
    const db = await getDb();
    const collection = db.collection('backlink_analyses');

    // First, verify the analysis belongs to the user
    const analysis = await collection.findOne({
      _id: analysisObjectId,
      userId: session.user.id,
    });

    if (!analysis) {
      return NextResponse.json({ 
        error: 'Analysis not found or access denied' 
      }, { status: 404 });
    }

    // Update the backlinks for the specific competitor
    const result = await collection.updateOne(
      {
        _id: analysisObjectId,
        'analysisResults.url': competitorUrl,
      },
      {
        $set: {
          'analysisResults.$.backlinks': backlinks,
          updatedAt: new Date(),
        }
      }
    );

    if (result.modifiedCount === 0) {
      return NextResponse.json({ 
        error: 'Competitor not found in analysis' 
      }, { status: 404 });
    }

    const competitorUrlHash = createHash('sha256').update(competitorUrl).digest('hex').slice(0, 12);
    console.log('[Backlinks] Updated competitor backlinks', {
      analysisId,
      competitorUrlHash,
      backlinksCount: Array.isArray(backlinks) ? backlinks.length : 0,
    });

    return NextResponse.json({
      success: true,
      message: 'Backlinks updated successfully',
    });

  } catch (error: any) {
    const errorId = randomUUID();
    console.error('Update competitor backlinks error:', errorId, error);
    return NextResponse.json({ 
      error: 'Failed to update backlinks. Please try again later.',
      errorId,
    }, { status: 500 });
  }
}
