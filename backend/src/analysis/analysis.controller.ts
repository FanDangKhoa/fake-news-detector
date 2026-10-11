import { Body, Controller, Get, Post, Query } from '@nestjs/common';
import { AnalysisService } from './analysis.service';
import { AnalyzeTextDto } from './dto/analyze-text.dto';

@Controller('analysis')
export class AnalysisController {
  constructor(private readonly analysisService: AnalysisService) {}

  @Post()
  analyze(@Body() dto: AnalyzeTextDto) {
    return this.analysisService.analyze(dto.text);
  }

  @Get('history')
  history(@Query('limit') limit?: string) {
    return this.analysisService.getHistory(limit ? Number(limit) : 20);
  }

  @Get('stats')
  stats() {
    return this.analysisService.getStats();
  }
}
