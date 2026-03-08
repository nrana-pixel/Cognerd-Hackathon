/**
 * DataForSEO Backlinks API Client
 * 
 * Provides methods to fetch backlink data for competitor analysis
 * Documentation: https://docs.dataforseo.com/v3/backlinks/overview/
 */

// ==================== Types ====================

export interface BacklinkSummary {
  target: string;
  rank: number;
  backlinks: number;
  backlinksSpamScore: number;
  brokenBacklinks: number;
  referringDomains: number;
  referringDomainsNofollow: number;
  referringMainDomains: number;
  referringIps: number;
  referringSubnets: number;
  referringPages: number;
  referringPagesNofollow: number;
  firstSeen: string | null;
  lostDate: string | null;
  externalLinksCount: number;
  internalLinksCount: number;
  info?: {
    server?: string;
    cms?: string;
    platformType?: string[];
    ipAddress?: string;
    country?: string;
    isIp?: boolean;
    targetSpamScore?: number;
  };
  referringLinksTld?: Record<string, number>;
  referringLinksTypes?: Record<string, number>;
  referringLinksAttributes?: Record<string, number>;
  referringLinksPlatformTypes?: Record<string, number>;
  referringLinksSemanticLocations?: Record<string, number>;
  referringLinksCountries?: Record<string, number>;
}

export interface Backlink {
  type: string;
  domainFrom: string;
  urlFrom: string;
  urlFromHttps: boolean;
  domainTo: string;
  urlTo: string;
  urlToHttps: boolean;
  tldFrom: string;
  isNew: boolean;
  isLost: boolean;
  backlinkSpamScore: number;
  rank: number;
  pageFromRank: number;
  domainFromRank: number;
  domainFromPlatformType: string[];
  domainFromCountry: string;
  pageFromExternalLinks: number;
  pageFromInternalLinks: number;
  pageFromSize: number;
  pageFromEncoding: string;
  pageFromLanguage: string;
  pageFromTitle: string;
  pageFromStatusCode: number;
  firstSeen: string;
  lastSeen: string;
  itemType: string;
  attributes: string[];
  dofollow: boolean;
  anchor: string;
  textPre: string | null;
  textPost: string | null;
  semanticLocation: string | null;
  linksCount: number;
  isBroken: boolean;
}

export interface CompetitorBacklinkData {
  competitor: string;
  url: string;
  summary: BacklinkSummary | null;
  backlinks: Backlink[];
  error?: string;
  analysisId?: string; // Track which analysis this competitor came from (for history)
  analysisDate?: string; // When this analysis was performed
}

export interface DataForSEOResponse<T> {
  version: string;
  statusCode: number;
  statusMessage: string;
  time: string;
  cost: number;
  tasksCount: number;
  tasksError: number;
  tasks: Array<{
    id: string;
    statusCode: number;
    statusMessage: string;
    time: string;
    cost: number;
    resultCount: number;
    path: string[];
    data: any;
    result: T[];
  }>;
}

// ==================== Client ====================

export class DataForSEOClient {
  private baseUrl = 'https://api.dataforseo.com/v3';
  private authHeader: string;

  constructor() {
    const login = process.env.DATAFORSEO_LOGIN;
    const password = process.env.DATAFORSEO_PASSWORD;

    if (!login || !password) {
      throw new Error('DataForSEO credentials not configured. Set DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD environment variables.');
    }

    // Basic Auth: base64 encode "login:password"
    this.authHeader = 'Basic ' + Buffer.from(`${login}:${password}`).toString('base64');
  }

  /**
   * Make authenticated request to DataForSEO API
   */
  private async request<T>(endpoint: string, body: any[]): Promise<DataForSEOResponse<T>> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: 'POST',
      headers: {
        'Authorization': this.authHeader,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      throw new Error(`DataForSEO API error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  private hashTarget(target: string): string {
    return Buffer.from(target).toString('base64').slice(0, 12);
  }

  /**
   * Get backlink summary for a target domain
   * Returns overview stats: total backlinks, referring domains, rank, etc.
   */
  async getBacklinksSummary(target: string): Promise<BacklinkSummary | null> {
    try {
      // Clean target URL - extract domain
      const cleanTarget = this.extractDomain(target);
      console.log('[DataForSEO] Fetching backlinks summary', { targetHash: this.hashTarget(cleanTarget) });
      
      const response = await this.request<any>('/backlinks/summary/live', [{
        target: cleanTarget,
        include_subdomains: true,
        backlinks_status_type: 'live',
        internal_list_limit: 10,
      }]);

      console.log('[DataForSEO] Backlinks summary request completed', {
        targetHash: this.hashTarget(cleanTarget),
        tasksCount: response.tasks?.length || 0,
      });

      if (response.tasks?.[0]?.result?.[0]) {
        const result = response.tasks[0].result[0];
        return this.mapSummaryResponse(result);
      }

      console.log('[DataForSEO] No summary result received', {
        targetHash: this.hashTarget(cleanTarget),
      });
      return null;
    } catch (error) {
      console.error(`[DataForSEO] Failed to get backlinks summary for ${target}:`, error);
      throw error;
    }
  }

  /**
   * Get list of backlinks for a target domain
   * Fetches a mix of DoFollow (70%) and NoFollow (30%) backlinks
   */
  async getBacklinks(target: string, limit: number = 100): Promise<Backlink[]> {
    try {
      const cleanTarget = this.extractDomain(target);
      
      // Calculate split: 70% DoFollow, 30% NoFollow
      const doFollowLimit = Math.ceil(limit * 0.7);
      const noFollowLimit = Math.floor(limit * 0.3);
      
      console.log('[DataForSEO] Fetching backlinks mix', {
        targetHash: this.hashTarget(cleanTarget),
        doFollowLimit,
        noFollowLimit,
      });
      
      // Fetch DoFollow backlinks
      const doFollowResponse = await this.request<any>('/backlinks/backlinks/live', [{
        target: cleanTarget,
        mode: 'as_is',
        limit: Math.min(doFollowLimit, 1000),
        backlinks_status_type: 'live',
        include_subdomains: true,
        order_by: ['rank,desc'],
        filters: [['dofollow', '=', true]],
      }]);
      
      // Fetch NoFollow backlinks
      const noFollowResponse = await this.request<any>('/backlinks/backlinks/live', [{
        target: cleanTarget,
        mode: 'as_is',
        limit: Math.min(noFollowLimit, 1000),
        backlinks_status_type: 'live',
        include_subdomains: true,
        order_by: ['rank,desc'],
        filters: [['dofollow', '=', false]],
      }]);

      const doFollowLinks = doFollowResponse.tasks?.[0]?.result?.[0]?.items || [];
      const noFollowLinks = noFollowResponse.tasks?.[0]?.result?.[0]?.items || [];
      
      console.log('[DataForSEO] Backlinks fetch completed', {
        targetHash: this.hashTarget(cleanTarget),
        doFollowCount: doFollowLinks.length,
        noFollowCount: noFollowLinks.length,
      });
      
      // Combine and map
      const allBacklinks = [
        ...doFollowLinks.map((item: any) => this.mapBacklinkResponse(item)),
        ...noFollowLinks.map((item: any) => this.mapBacklinkResponse(item)),
      ];

      return allBacklinks;
    } catch (error) {
      console.error(`Failed to get backlinks for ${target}:`, error);
      throw error;
    }
  }

  /**
   * Get backlink data for multiple competitors
   */
  async getCompetitorsBacklinks(
    competitors: Array<{ name: string; url: string }>,
    options: { includeSummary?: boolean; includeBacklinks?: boolean; backlinksLimit?: number } = {}
  ): Promise<CompetitorBacklinkData[]> {
    const { includeSummary = true, includeBacklinks = false, backlinksLimit = 50 } = options;

    const results: CompetitorBacklinkData[] = [];

    for (const competitor of competitors) {
      try {
        const data: CompetitorBacklinkData = {
          competitor: competitor.name,
          url: competitor.url,
          summary: null,
          backlinks: [],
        };

        if (includeSummary) {
          data.summary = await this.getBacklinksSummary(competitor.url);
        }

        if (includeBacklinks) {
          data.backlinks = await this.getBacklinks(competitor.url, backlinksLimit);
        }

        results.push(data);
      } catch (error: any) {
        results.push({
          competitor: competitor.name,
          url: competitor.url,
          summary: null,
          backlinks: [],
          error: error.message || 'Failed to fetch backlink data',
        });
      }
    }

    return results;
  }

  /**
   * Extract domain from URL
   */
  private extractDomain(url: string): string {
    try {
      // If already looks like a domain (no protocol), return as-is
      if (!url.includes('://')) {
        return url.replace(/\/.*$/, '').toLowerCase();
      }
      const urlObj = new URL(url);
      return urlObj.hostname.toLowerCase();
    } catch {
      // Fallback: just clean up the string
      return url.replace(/^https?:\/\//, '').replace(/\/.*$/, '').toLowerCase();
    }
  }

  /**
   * Map API response to BacklinkSummary type
   */
  private mapSummaryResponse(data: any): BacklinkSummary {
    return {
      target: data.target || '',
      rank: data.rank || 0,
      backlinks: data.backlinks || 0,
      backlinksSpamScore: data.backlinks_spam_score || 0,
      brokenBacklinks: data.broken_backlinks || 0,
      referringDomains: data.referring_domains || 0,
      referringDomainsNofollow: data.referring_domains_nofollow || 0,
      referringMainDomains: data.referring_main_domains || 0,
      referringIps: data.referring_ips || 0,
      referringSubnets: data.referring_subnets || 0,
      referringPages: data.referring_pages || 0,
      referringPagesNofollow: data.referring_pages_nofollow || 0,
      firstSeen: data.first_seen || null,
      lostDate: data.lost_date || null,
      externalLinksCount: data.external_links_count || 0,
      internalLinksCount: data.internal_links_count || 0,
      info: data.info ? {
        server: data.info.server,
        cms: data.info.cms,
        platformType: data.info.platform_type,
        ipAddress: data.info.ip_address,
        country: data.info.country,
        isIp: data.info.is_ip,
        targetSpamScore: data.info.target_spam_score,
      } : undefined,
      referringLinksTld: data.referring_links_tld,
      referringLinksTypes: data.referring_links_types,
      referringLinksAttributes: data.referring_links_attributes,
      referringLinksPlatformTypes: data.referring_links_platform_types,
      referringLinksSemanticLocations: data.referring_links_semantic_locations,
      referringLinksCountries: data.referring_links_countries,
    };
  }

  /**
   * Map API response to Backlink type
   */
  private mapBacklinkResponse(data: any): Backlink {
    return {
      type: data.type || '',
      domainFrom: data.domain_from || '',
      urlFrom: data.url_from || '',
      urlFromHttps: data.url_from_https || false,
      domainTo: data.domain_to || '',
      urlTo: data.url_to || '',
      urlToHttps: data.url_to_https || false,
      tldFrom: data.tld_from || '',
      isNew: data.is_new || false,
      isLost: data.is_lost || false,
      backlinkSpamScore: data.backlink_spam_score || 0,
      rank: data.rank || 0,
      pageFromRank: data.page_from_rank || 0,
      domainFromRank: data.domain_from_rank || 0,
      domainFromPlatformType: data.domain_from_platform_type || [],
      domainFromCountry: data.domain_from_country || '',
      pageFromExternalLinks: data.page_from_external_links || 0,
      pageFromInternalLinks: data.page_from_internal_links || 0,
      pageFromSize: data.page_from_size || 0,
      pageFromEncoding: data.page_from_encoding || '',
      pageFromLanguage: data.page_from_language || '',
      pageFromTitle: data.page_from_title || '',
      pageFromStatusCode: data.page_from_status_code || 0,
      firstSeen: data.first_seen || '',
      lastSeen: data.last_seen || '',
      itemType: data.item_type || '',
      attributes: data.attributes || [],
      dofollow: data.dofollow || false,
      anchor: data.anchor || '',
      textPre: data.text_pre || null,
      textPost: data.text_post || null,
      semanticLocation: data.semantic_location || null,
      linksCount: data.links_count || 0,
      isBroken: data.is_broken || false,
    };
  }
}

/**
 * Create singleton instance (lazy initialization)
 */
let clientInstance: DataForSEOClient | null = null;

export function getDataForSEOClient(): DataForSEOClient {
  if (!clientInstance) {
    clientInstance = new DataForSEOClient();
  }
  return clientInstance;
}
