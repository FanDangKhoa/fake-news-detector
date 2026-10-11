import {
  Column,
  CreateDateColumn,
  Entity,
  PrimaryGeneratedColumn,
} from 'typeorm';

@Entity('analyses')
export class Analysis {
  @PrimaryGeneratedColumn()
  id: number;

  @Column({ type: 'text' })
  text: string;

  @Column({ type: 'varchar', length: 10 })
  label: 'fake' | 'real';

  @Column({ type: 'float' })
  confidence: number;

  @CreateDateColumn()
  createdAt: Date;
}
