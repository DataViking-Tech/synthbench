export interface LeaderboardEntry {
	rank: number;
	provider: string;
	model: string;
	dataset: string;
	sps: number;
	jsd: number;
	tau: number;
	n: number;
	ci_lower: number;
	ci_upper: number;
	temperature?: number;
	template?: string;
	is_baseline: boolean;
	is_ensemble: boolean;
	topic_scores?: Record<string, number>;
	replicates?: ReplicateRun[];
}

export interface ReplicateRun {
	rep: number;
	sps: number;
	jsd: number;
	tau: number;
}

export interface LeaderboardData {
	generated_at: string;
	synthbench_version: string;
	datasets: string[];
	entries: LeaderboardEntry[];
	convergence?: ConvergencePoint[];
}

export interface ConvergencePoint {
	model: string;
	dataset: string;
	rep_count: number;
	sps: number;
}
