import { Injectable } from '@nestjs/common';

@Injectable()
export class AnalysisService {
  analyze(text: string) {
    const fakeScore = Math.random();

    return {
      text,
      label: fakeScore > 0.5 ? 'fake' : 'real',
      confidence: Math.round(fakeScore * 100) / 100,
      analyzedAt: new Date().toISOString(),
    };
  }
}