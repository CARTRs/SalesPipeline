export interface Opportunity {
  id: number;
  code: string;
  customerId: number;
  customerName?: string;
  accountManagerId: number;
  visitContent: string;
  aiAnalysis?: AIAnalysis;
  status: number;
  statusText?: string;
  estimateAmount: number | null;
  urgencyLevel: number;
  currentNode: string;
  nodeDeadline: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface AIAnalysis {
  opportunityType: string;
  customerIndustry: string;
  estimateAmount?: {
    min: number;
    max: number;
    unit: string;
  };
  urgencyLevel: string;
  keyRequirements: string[];
  decisionChain: { role: string; name?: string }[];
  nextSteps: string;
  confidence: number;
}

export interface User {
  id: number;
  username: string;
  realName: string;
  role: string;
  phone?: string;
  email?: string;
}

export interface Project {
  id: number;
  opportunityId: number;
  projectManagerId?: number;
  teamMembers?: ProjectMember[];
  schedulePlan?: SchedulePlan;
  status: number;
}

export interface ProjectMember {
  id: number;
  projectId: number;
  userId: number;
  role: string;
  joinTime: string;
}

export interface SchedulePlan {
  phases: SchedulePhase[];
}

export interface SchedulePhase {
  name: string;
  userId: number;
  startDate: string;
  endDate: string;
}
