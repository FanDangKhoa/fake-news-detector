import { IsNotEmpty, IsString, MinLength } from 'class-validator';

export class AnalyzeTextDto {
  @IsString()
  @IsNotEmpty()
  @MinLength(10, { message: 'Văn bản cần ít nhất 10 ký tự' })
  text: string;
}