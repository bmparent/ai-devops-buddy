import { vi, test, expect } from "vitest";
import { render, screen, waitFor } from '@testing-library/react';
import App from './App';

global.fetch = vi.fn(() =>
  Promise.resolve({ json: () => Promise.resolve({ ping: 'pong' }) })
);

test('displays ping', async () => {
  render(<App />);
  await waitFor(() => {
    expect(screen.getByText('pong')).toBeTruthy();
  });
});
