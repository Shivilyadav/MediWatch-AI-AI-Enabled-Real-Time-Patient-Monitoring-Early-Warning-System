/**
 * Utility formatters for timestamps, physiological vitals, and risk levels.
 */

export function formatTimestamp(isoStringOrDate) {
  if (!isoStringOrDate) return 'N/A';
  const date = new Date(isoStringOrDate);
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

export function formatDate(isoStringOrDate) {
  if (!isoStringOrDate) return 'N/A';
  const date = new Date(isoStringOrDate);
  return date.toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

export function formatTimeAgo(isoStringOrDate) {
  if (!isoStringOrDate) return 'Just now';
  const diffMs = new Date() - new Date(isoStringOrDate);
  const diffSecs = Math.floor(diffMs / 1000);
  
  if (diffSecs < 10) return 'Just now';
  if (diffSecs < 60) return `${diffSecs}s ago`;
  const diffMins = Math.floor(diffSecs / 60);
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  return `${diffHours}h ago`;
}

export function getRiskColor(level) {
  switch (level?.toUpperCase()) {
    case 'CRITICAL':
      return {
        bg: 'bg-red-500/20',
        text: 'text-red-400',
        border: 'border-red-500/50',
        hex: '#D32F2F',
        glow: 'animate-critical-glow',
        badgeBg: 'bg-red-950/80',
        badgeText: 'text-red-300'
      };
    case 'HIGH':
      return {
        bg: 'bg-orange-500/20',
        text: 'text-orange-400',
        border: 'border-orange-500/50',
        hex: '#F57C00',
        glow: 'animate-high-glow',
        badgeBg: 'bg-orange-950/80',
        badgeText: 'text-orange-300'
      };
    case 'MEDIUM':
      return {
        bg: 'bg-yellow-500/20',
        text: 'text-yellow-400',
        border: 'border-yellow-500/50',
        hex: '#FBC02D',
        glow: '',
        badgeBg: 'bg-yellow-950/80',
        badgeText: 'text-yellow-300'
      };
    case 'NORMAL':
    case 'LOW':
    default:
      return {
        bg: 'bg-emerald-500/20',
        text: 'text-emerald-400',
        border: 'border-emerald-500/50',
        hex: '#388E3C',
        glow: '',
        badgeBg: 'bg-emerald-950/80',
        badgeText: 'text-emerald-300'
      };
  }
}

export function getVitalStatus(vitalName, value) {
  switch (vitalName) {
    case 'heart_rate':
      if (value < 50) return { label: 'Bradycardia', severity: 'HIGH' };
      if (value > 120) return { label: 'Severe Tachycardia', severity: 'CRITICAL' };
      if (value > 100) return { label: 'Elevated', severity: 'MEDIUM' };
      return { label: 'Normal', severity: 'NORMAL' };
    case 'spo2':
      if (value < 88) return { label: 'Severe Hypoxia', severity: 'CRITICAL' };
      if (value <= 92) return { label: 'Hypoxic', severity: 'HIGH' };
      if (value <= 94) return { label: 'Borderline', severity: 'MEDIUM' };
      return { label: 'Normal', severity: 'NORMAL' };
    case 'respiratory_rate':
      if (value < 9) return { label: 'Bradypnea', severity: 'CRITICAL' };
      if (value >= 25) return { label: 'Tachypnea', severity: 'CRITICAL' };
      if (value >= 21) return { label: 'Elevated', severity: 'HIGH' };
      return { label: 'Normal', severity: 'NORMAL' };
    case 'temperature':
      if (value >= 39.0) return { label: 'High Fever', severity: 'HIGH' };
      if (value >= 38.0) return { label: 'Fever', severity: 'MEDIUM' };
      if (value < 36.0) return { label: 'Hypothermia', severity: 'HIGH' };
      return { label: 'Normal', severity: 'NORMAL' };
    default:
      return { label: 'Normal', severity: 'NORMAL' };
  }
}
