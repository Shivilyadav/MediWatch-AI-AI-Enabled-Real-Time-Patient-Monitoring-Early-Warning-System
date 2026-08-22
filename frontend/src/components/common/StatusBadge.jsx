import React from 'react';
import { getRiskColor } from '../../utils/formatters';

export function StatusBadge({ level, showDot = true, className = '' }) {
  const styles = getRiskColor(level);

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold border tracking-wide uppercase ${styles.badgeBg} ${styles.badgeText} ${styles.border} ${className}`}>
      {showDot && (
        <span className={`w-2 h-2 rounded-full ${styles.text} bg-current ${level === 'CRITICAL' ? 'animate-ping' : ''}`} />
      )}
      {level}
    </span>
  );
}
