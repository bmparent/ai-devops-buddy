import { render, screen, waitFor } from '@testing-library/react';
import matchers from '@testing-library/jest-dom/matchers';
import { describe, it, vi, expect } from 'vitest';
import App from '../App';
import * as api from '../api';

expect.extend(matchers);
vi.mock('../api');

describe('App', () => {
  it('renders message from API', async () => {
    (api.getMessage as vi.Mock).mockResolvedValue('Hello from FastAPI');
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText('Hello from FastAPI')).toBeInTheDocument();
    });
  });
});
