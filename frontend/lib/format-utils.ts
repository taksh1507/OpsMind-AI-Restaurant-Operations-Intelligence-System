/**
 * Format number as Indian Rupee with en-IN locale
 * @param amount - The numeric amount to format (can be null/undefined)
 * @returns Formatted string with ₹ symbol (e.g., ₹1,00,000)
 */
export function formatRupee(amount?: number | null): string {
  if (amount === null || amount === undefined) {
    return '₹0';
  }

  try {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    }).format(amount);
  } catch (error) {
    console.error('Error formatting rupee:', error);
    return '₹0';
  }
}

/**
 * Format number as percentage
 * @param value - The numeric value to format as percentage
 * @returns Formatted string with % symbol (e.g., 45.2%)
 */
export function formatPercentage(value?: number | null): string {
  if (value === null || value === undefined) {
    return '0%';
  }

  return `${value.toFixed(1)}%`;
}

/**
 * Format large numbers with K, M, B suffix
 * @param num - The number to format
 * @returns Formatted string (e.g., 1.2K, 2.5M)
 */
export function formatCompact(num?: number | null): string {
  if (num === null || num === undefined) {
    return '0';
  }

  const absNum = Math.abs(num);

  if (absNum >= 1000000000) {
    return `${(num / 1000000000).toFixed(1)}B`;
  }
  if (absNum >= 1000000) {
    return `${(num / 1000000).toFixed(1)}M`;
  }
  if (absNum >= 1000) {
    return `${(num / 1000).toFixed(1)}K`;
  }

  return num.toString();
}
