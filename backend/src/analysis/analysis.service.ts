import { HttpException, HttpStatus, Injectable } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { firstValueFrom } from 'rxjs';
import { AxiosError } from 'axios';
type PredictResponse = {
  text: string;
  label: 'fake' | 'real';
  confidence: number;
};
@Injectable()
export class AnalysisService {
  constructor(private readonly httpService: HttpService) {}
  async analyze(text: string) {
    try {
      const response = await firstValueFrom(
        this.httpService.post<PredictResponse>('/predict', { text }),
      );
      return {
        text: response.data.text,
        label: response.data.label,
        confidence: response.data.confidence,
        analyzedAt: new Date().toISOString(),
      };
    } catch (error) {
      const axiosError = error as AxiosError;
      throw new HttpException(
        'Không thể kết nối đến AI service. Hãy kiểm tra FastAPI đã chạy ở port 8000 chưa.',
        axiosError.response?.status || HttpStatus.SERVICE_UNAVAILABLE,
      );
    }
  }
}
