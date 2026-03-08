import { ObjectId } from 'mongodb';
import type { CompetitorBacklinkData } from '../dataforseo';

/**
 * MongoDB Schema for Backlinks Analysis History
 * Collection: backlink_analyses
 */
export interface BacklinkAnalysis {
  _id?: ObjectId;
  userId: string;
  brandId: string;
  brandName: string;
  brandUrl: string;
  
  // Analysis results - array of competitor backlink data
  analysisResults: CompetitorBacklinkData[];
  
  // Metadata
  competitorsCount: number;
  totalBacklinks: number;
  totalReferringDomains: number;
  
  createdAt: Date;
  updatedAt: Date;
}
