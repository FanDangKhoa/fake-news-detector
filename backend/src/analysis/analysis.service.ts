import { HttpException, HttpStatus, Injectable } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { firstValueFrom } from 'rxjs';
import { Analysis } from './entities/analysis.entity';

type PredictResponse = {
  text: string;
  label: 'fake' | 'real';
  confidence: number;
};

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
      confidence: saved.confidence,
      analyzedAt: saved.createdAt.toISOString(),
    };
  }

  async getHistory(limit = 20) {
    return this.repo.find({
      order: { createdAt: 'DESC' },
      take: Math.min(limit, 100),
    });
  }

  async getStats() {
    const total = await this.repo.count();
    const fake = await this.repo.count({ where: { label: 'fake' } });

    const daily = await this.repo
      .createQueryBuilder('a')
      .select("TO_CHAR(a.createdAt, 'YYYY-MM-DD')", 'date')
      .addSelect('COUNT(*)', 'total')
      .addSelect("SUM(CASE WHEN a.label = 'fake' THEN 1 ELSE 0 END)", 'fake')
      .where("a.createdAt >= NOW() - INTERVAL '7 days'")
      .groupBy('date')
      .orderBy('date', 'ASC')
      .getRawMany();

    return {
      total,
      fake,
      real: total - fake,
      daily: daily.map((d) => ({
        date: d.date as string,
        total: Number(d.total),
        fake: Number(d.fake),
      })),
    };
  }
}
