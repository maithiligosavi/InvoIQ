import {
  Bar,
  BarChart,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { BarChart3, PieChart as PieIcon } from 'lucide-react';
import { formatINR } from '@/utils/format';
import type { Analytics } from '@/types';

interface ChartsProps {
  analytics: Analytics;
}

const PIE_COLORS = ['#2563eb', '#0ea5e9', '#10b981', '#f59e0b', '#ef4444'];

function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white rounded-lg border border-slate-200 shadow-card px-3 py-2">
      {label && <p className="text-xs font-semibold text-slate-700 mb-1">{label}</p>}
      {payload.map((entry: any, i: number) => (
        <p key={i} className="text-xs text-slate-600">
          <span
            className="inline-block w-2 h-2 rounded-full mr-1.5 align-middle"
            style={{ background: entry.color || entry.fill }}
          />
          {entry.name}: {formatINR(entry.value)}
        </p>
      ))}
    </div>
  );
}

export default function Charts({ analytics }: ChartsProps) {
  const monthlySpend = analytics?.monthlySpend || [];
  const vendorSpend = analytics?.vendorSpend || [];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
      <div className="lg:col-span-3 bg-white rounded-xl border border-slate-200 p-5 shadow-soft animate-fade-in">
        <div className="flex items-center gap-2 mb-4">
          <BarChart3 size={18} className="text-brand-600" />
          <h3 className="text-sm font-bold text-slate-900">Monthly Spend Overview</h3>
        </div>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={monthlySpend} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
            <XAxis
              dataKey="month"
              tick={{ fontSize: 12, fill: '#64748b' }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: '#94a3b8' }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => `₹${v / 1000}k`}
            />
            <Tooltip content={<ChartTooltip />} cursor={{ fill: '#f8fafc' }} />
            <Bar dataKey="spend" name="Spend" radius={[5, 5, 0, 0]} maxBarSize={42}>
              {monthlySpend.map((_, i) => (
                <Cell key={i} fill="#2563eb" />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 p-5 shadow-soft animate-fade-in">
        <div className="flex items-center gap-2 mb-4">
          <PieIcon size={18} className="text-brand-600" />
          <h3 className="text-sm font-bold text-slate-900">Spend by Top Vendors</h3>
        </div>
        {vendorSpend.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-[300px] text-slate-400 text-xs text-center px-4">
            <p className="font-medium text-slate-500">No vendor spending recorded yet</p>
            <p className="mt-1 text-slate-400">Upload invoices to view distribution by vendor</p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={vendorSpend}
                dataKey="spend"
                nameKey="vendor"
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={95}
                paddingAngle={3}
              >
                {vendorSpend.map((_, i) => (
                  <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip content={<ChartTooltip />} />
              <Legend
                iconType="circle"
                wrapperStyle={{ fontSize: 11 }}
              />
            </PieChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
