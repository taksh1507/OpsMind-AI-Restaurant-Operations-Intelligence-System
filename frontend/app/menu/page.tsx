'use client'

import { StatCard } from '@/components/ui'
import { UtensilsCrossed } from 'lucide-react'

export default function MenuPage() {
  const menuCategories = [
    { name: 'Appetizers', items: 12, revenue: '$3,240' },
    { name: 'Main Courses', items: 28, revenue: '$12,890' },
    { name: 'Desserts', items: 8, revenue: '$2,150' },
    { name: 'Beverages', items: 15, revenue: '$4,320' },
  ]

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="border-b border-electric-500/20 pb-6">
        <h1 className="text-4xl font-bold bg-gradient-to-r from-slate-50 to-electric-300 bg-clip-text text-transparent mb-2 flex items-center gap-3">
          <UtensilsCrossed size={32} className="text-electric-400" />
          Menu Management
        </h1>
        <p className="text-slate-400">
          View and manage all menu items and categories
        </p>
      </div>

      {/* Menu Categories Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {menuCategories.map((category) => (
          <StatCard
            key={category.name}
            title={category.name}
            value={`${category.items}`}
            description={`Revenue: ${category.revenue}`}
            icon={<UtensilsCrossed size={24} />}
          />
        ))}
      </div>

      {/* Menu Items Sample */}
      <div className="p-6 rounded-xl border border-electric-500/30 bg-slate-800/30 backdrop-blur-sm">
        <h2 className="text-xl font-semibold text-slate-50 mb-6">
          Top Performing Items
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-electric-500/20">
                <th className="text-left py-3 px-4 text-slate-400">Item Name</th>
                <th className="text-left py-3 px-4 text-slate-400">Category</th>
                <th className="text-right py-3 px-4 text-slate-400">Sales</th>
                <th className="text-right py-3 px-4 text-slate-400">Revenue</th>
              </tr>
            </thead>
            <tbody>
              {[
                { name: 'Margherita Pizza', category: 'Main Courses', sales: 23, revenue: '$345' },
                { name: 'Grilled Salmon', category: 'Main Courses', sales: 18, revenue: '$252' },
                { name: 'Caesar Salad', category: 'Appetizers', sales: 15, revenue: '$105' },
                { name: 'Tiramisu', category: 'Desserts', sales: 22, revenue: '$176' },
              ].map((item, idx) => (
                <tr key={idx} className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors">
                  <td className="py-3 px-4 text-slate-200">{item.name}</td>
                  <td className="py-3 px-4 text-slate-400">{item.category}</td>
                  <td className="py-3 px-4 text-right text-electric-300">{item.sales}</td>
                  <td className="py-3 px-4 text-right text-electric-400 font-semibold">{item.revenue}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
