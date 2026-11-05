import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { SearchScopeSelector } from './SearchScopeSelector';
import type { Document } from '../types/api';

describe('SearchScopeSelector', () => {
  const readyDoc: Document = {
    id: '1', filename: 'ready.txt', format: 'txt', status: 'ready',
    error_code: null, error_message: null, size_bytes: 100, created_at: '2026-11-04T10:00:00Z'
  };
  const errorDoc: Document = {
    id: '2', filename: 'error.txt', format: 'txt', status: 'error',
    error_code: 'invalid_encoding', error_message: 'Err', size_bytes: 100, created_at: '2026-11-04T10:00:00Z'
  };

  it('показывает только готовые документы в списке', async () => {
    render(
      <SearchScopeSelector 
        documents={[readyDoc, errorDoc]} 
        selectedIds={null} 
        onChange={() => {}} 
      />
    );
    
    // Открываем выпадашку
    await userEvent.click(screen.getByText('Все документы'));
    
    // Готовый документ должен быть
    expect(screen.getByText('ready.txt')).toBeInTheDocument();
    
    // Документ с ошибкой не должен отображаться
    expect(screen.queryByText('error.txt')).not.toBeInTheDocument();
  });

  it('передает массив ID при выборе документа', async () => {
    const handleChange = vi.fn();
    render(
      <SearchScopeSelector 
        documents={[readyDoc]} 
        selectedIds={null} 
        onChange={handleChange} 
      />
    );
    
    await userEvent.click(screen.getByText('Все документы'));
    await userEvent.click(screen.getByText('ready.txt'));
    
    expect(handleChange).toHaveBeenCalledWith(['1']);
  });
});
