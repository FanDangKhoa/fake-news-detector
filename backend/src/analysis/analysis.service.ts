import { HttpException, HttpStatus, Injectable } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { InjectRepository } from '@nestjs/typeorm';
import { LessThan, MoreThanOrEqual, Repository } from 'typeorm';
import { firstValueFrom } from 'rxjs';
import { Analysis } from './entities/analysis.entity';

type Evidence = {
  text: string;
  source: string;
  topic: string;
  url: string;
  score: number;
};

type Claim = {
  text: string;
  evidence: Evidence[];
};

type PredictResponse = {
  text: string;
  label: 'fake' | 'real';
  confidence: number;
  claims?: Claim[];
};

type Verdict = 'fake' | 'real' | 'uncertain';

// Độ tin cậy dưới ngưỡng này thì không đưa ra kết luận giả/thật.
export const CONFIDENCE_THRESHOLD = 0.8;

function toVerdict(label: 'fake' | 'real', confidence: number): Verdict {
  return confidence < CONFIDENCE_THRESHOLD ? 'uncertain' : label;
}

@Injectable()
export class AnalysisService {
  constructor(
    private readonly httpService: HttpService,
    @InjectRepository(Analysis)
    private readonly repo: Repository<Analysis>,
  ) {}

  async analyze(text: string) {
    let prediction: PredictResponse;
    try {
      const response = await firstValueFrom(
        this.httpService.post<PredictResponse>('/predict', { text }),
      );
      prediction = response.data;
    } catch {
      throw new HttpException(
        'Không thể kết nối đến AI service. Hãy kiểm tra FastAPI đã chạy ở port 8000 chưa.',
        HttpStatus.SERVICE_UNAVAILABLE,
      );
    }

    const saved = await this.repo.save(
      this.repo.create({
        text: prediction.text,
        label: prediction.label,
        confidence: prediction.confidence,
      }),
    );

    return {
      id: saved.id,
      text: saved.text,
      label: saved.label,
      verdict: toVerdict(saved.label, saved.confidence),
      confidence: saved.confidence,
      analyzedAt: saved.createdAt.toISOString(),
      threshold: CONFIDENCE_THRESHOLD,
      claims: prediction.claims ?? [],
    };
  }

  async getHistory(limit = 20) {
    const rows = await this.repo.find({
      order: { createdAt: 'DESC' },
      take: Math.min(limit, 100),
    });
    return rows.map((r) => ({
      ...r,
      verdict: toVerdict(r.label, r.confidence),
    }));
  }

  async getStats() {
    const t = CONFIDENCE_THRESHOLD;

    const total = await this.repo.count();
    const uncertain = await this.repo.count({
      where: { confidence: LessThan(t) },
    });
    const fake = await this.repo.count({
      where: { label: 'fake', confidence: MoreThanOrEqual(t) },
    });

    // t là hằng số số học do server định nghĩa, không phải dữ liệu người dùng.
    const daily = await this.repo
      .createQueryBuilder('a')
      .select("TO_CHAR(a.createdAt, 'YYYY-MM-DD')", 'date')
      .addSelect('COUNT(*)', 'total')
      .addSelect(`SUM(CASE WHEN a.confidence < ${t} THEN 1 ELSE 0 END)`, 'uncertain')
      .addSelect(
        `SUM(CASE WHEN a.confidence >= ${t} AND a.label = 'fake' THEN 1 ELSE 0 END)`,
        'fake',
      )
      .where("a.createdAt >= NOW() - INTERVAL '7 days'")
      .groupBy('date')
      .orderBy('date', 'ASC')
      .getRawMany();

    return {
      threshold: t,
      total,
      fake,
      uncertain,
      real: total - fake - uncertain,
      daily: daily.map((d) => ({
        date: d.date as string,
        total: Number(d.total),
        fake: Number(d.fake),
        uncertain: Number(d.uncertain),
      })),
    };
  }
}
