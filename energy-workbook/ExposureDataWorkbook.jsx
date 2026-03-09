import React, { useState, useMemo } from 'react';
import { Download } from 'lucide-react';

// Sanitize a CSV cell value:
// - Escape embedded quotes by doubling them
// - Wrap in quotes if the value contains commas, newlines, or quotes
// - Prefix values starting with formula-triggering characters to prevent CSV injection
const csvEscape = (val) => {
  const s = String(val);
  // Prevent CSV injection (Excel/LibreOffice formula execution)
  if (/^[=+\-@]/.test(s)) {
    return `\t${s}`;
  }
  if (s.includes(',') || s.includes('\n') || s.includes('"')) {
    return `"${s.replace(/"/g, '""')}"`;
  }
  return s;
};

const ExposureDataWorkbook = () => {
  const [activeSheet, setActiveSheet] = useState('ISO_Tariffs');

  // ISO Tariffs Data
  const [isoTariffs, setIsoTariffs] = useState([
    { iso: 'CAISO', phase: 'Phase_1', milestone: 'Scoping', depositRequired: 10000, depositType: 'Fixed', refundable: 'No', withdrawalPenaltyPct: 0, studyCostForfeited: 'Yes' },
    { iso: 'CAISO', phase: 'Phase_2', milestone: 'System_Impact', depositRequired: 50000, depositType: 'Fixed', refundable: 'Partial', withdrawalPenaltyPct: 25, studyCostForfeited: 'Yes' },
    { iso: 'CAISO', phase: 'Phase_3', milestone: 'Facilities', depositRequired: 0, depositType: 'MW_Based', refundable: 'No', withdrawalPenaltyPct: 50, studyCostForfeited: 'Yes' },
    { iso: 'CAISO', phase: 'Phase_4', milestone: 'Construction', depositRequired: 0, depositType: 'MW_Based', refundable: 'No', withdrawalPenaltyPct: 100, studyCostForfeited: 'Yes' },
    { iso: 'MISO', phase: 'Phase_1', milestone: 'DPP', depositRequired: 10000, depositType: 'Fixed', refundable: 'No', withdrawalPenaltyPct: 0, studyCostForfeited: 'Yes' },
    { iso: 'MISO', phase: 'Phase_2', milestone: 'DPP_System', depositRequired: 50000, depositType: 'Fixed', refundable: 'Partial', withdrawalPenaltyPct: 20, studyCostForfeited: 'Yes' },
    { iso: 'MISO', phase: 'Phase_3', milestone: 'GIA_Execution', depositRequired: 100000, depositType: 'Fixed', refundable: 'No', withdrawalPenaltyPct: 75, studyCostForfeited: 'Yes' },
    { iso: 'ERCOT', phase: 'Phase_1', milestone: 'Screening', depositRequired: 5000, depositType: 'Fixed', refundable: 'No', withdrawalPenaltyPct: 10, studyCostForfeited: 'No' },
    { iso: 'ERCOT', phase: 'Phase_2', milestone: 'FS_Study', depositRequired: 25000, depositType: 'Fixed', refundable: 'Partial', withdrawalPenaltyPct: 30, studyCostForfeited: 'Yes' },
    { iso: 'ERCOT', phase: 'Phase_3', milestone: 'IA_Signed', depositRequired: 75000, depositType: 'MW_Based', refundable: 'No', withdrawalPenaltyPct: 50, studyCostForfeited: 'Yes' },
    { iso: 'PJM', phase: 'Phase_1', milestone: 'Feasibility', depositRequired: 10000, depositType: 'Fixed', refundable: 'No', withdrawalPenaltyPct: 0, studyCostForfeited: 'Yes' },
    { iso: 'PJM', phase: 'Phase_2', milestone: 'System_Impact', depositRequired: 50000, depositType: 'Fixed', refundable: 'Partial', withdrawalPenaltyPct: 25, studyCostForfeited: 'Yes' },
    { iso: 'PJM', phase: 'Phase_3', milestone: 'Facilities', depositRequired: 100000, depositType: 'MW_Based', refundable: 'Partial', withdrawalPenaltyPct: 50, studyCostForfeited: 'Yes' },
    { iso: 'SPP', phase: 'Phase_1', milestone: 'Definitive', depositRequired: 10000, depositType: 'Fixed', refundable: 'No', withdrawalPenaltyPct: 0, studyCostForfeited: 'Yes' },
    { iso: 'SPP', phase: 'Phase_2', milestone: 'Facilities', depositRequired: 50000, depositType: 'MW_Based', refundable: 'Partial', withdrawalPenaltyPct: 40, studyCostForfeited: 'Yes' },
  ]);

  // Projects Data
  const [projects, setProjects] = useState([
    { projectId: 'TX_Solar_001', iso: 'ERCOT', phase: 'Phase_2', mw: 150, depositPaid: 50000, studyCostsPaid: 125000, landOptionCost: 200000, transmissionDeposit: 500000, milestoneDate: '2024-06-15' },
    { projectId: 'CA_Wind_045', iso: 'CAISO', phase: 'Phase_3', mw: 200, depositPaid: 100000, studyCostsPaid: 350000, landOptionCost: 150000, transmissionDeposit: 1200000, milestoneDate: '2023-11-30' },
    { projectId: 'MO_Solar_023', iso: 'MISO', phase: 'Phase_2', mw: 100, depositPaid: 50000, studyCostsPaid: 200000, landOptionCost: 100000, transmissionDeposit: 750000, milestoneDate: '2024-03-20' },
    { projectId: 'PA_Storage_012', iso: 'PJM', phase: 'Phase_1', mw: 50, depositPaid: 10000, studyCostsPaid: 75000, landOptionCost: 50000, transmissionDeposit: 250000, milestoneDate: '2024-08-10' },
    { projectId: 'KS_Wind_067', iso: 'SPP', phase: 'Phase_2', mw: 300, depositPaid: 150000, studyCostsPaid: 400000, landOptionCost: 250000, transmissionDeposit: 1500000, milestoneDate: '2024-01-15' },
  ]);

  // Cost Categories Data
  const [costCategories, setCostCategories] = useState([
    { category: 'Land_Option', recoverableIfEarly: 'Yes', recoverableIfLate: 'No', timeThresholdDays: 180, notes: 'Before site control deadline' },
    { category: 'Study_Costs', recoverableIfEarly: 'No', recoverableIfLate: 'No', timeThresholdDays: 0, notes: 'Never recoverable per ISO tariff' },
    { category: 'Transmission_Deposit', recoverableIfEarly: 'Partial', recoverableIfLate: 'Partial', timeThresholdDays: 365, notes: 'Admin fee typically 10-25%' },
    { category: 'ISO_Deposit', recoverableIfEarly: 'Varies', recoverableIfLate: 'Varies', timeThresholdDays: 0, notes: 'See ISO_Tariffs table' },
    { category: 'Development_Costs', recoverableIfEarly: 'No', recoverableIfLate: 'No', timeThresholdDays: 0, notes: 'Internal sunk costs' },
    { category: 'Legal_Fees', recoverableIfEarly: 'No', recoverableIfLate: 'No', timeThresholdDays: 0, notes: 'Sunk costs' },
    { category: 'Engineering_Studies', recoverableIfEarly: 'No', recoverableIfLate: 'No', timeThresholdDays: 0, notes: 'Third party costs' },
  ]);

  // Custom Rules Data
  const [customRules, setCustomRules] = useState([
    { iso: 'CAISO', projectType: 'Storage', ruleOverride: 'Deposit_Multiplier', value: '1.5', effectiveDate: '2024-01-01', notes: 'CAISO storage surcharge' },
    { iso: 'MISO', projectType: 'Offshore_Wind', ruleOverride: 'Additional_Surety', value: '250000', effectiveDate: '2023-06-01', notes: 'Offshore complexity premium' },
    { iso: 'PJM', projectType: 'Solar_>200MW', ruleOverride: 'Study_Cost_Cap', value: '500000', effectiveDate: '2024-03-01', notes: 'Large project cap' },
    { iso: 'ERCOT', projectType: 'All', ruleOverride: 'Credit_Requirement', value: 'Investment_Grade', effectiveDate: '2024-01-01', notes: 'Updated credit policy' },
  ]);

  // MW Based Costs
  const [mwBasedCosts, setMwBasedCosts] = useState([
    { iso: 'CAISO', phase: 'Phase_3', costPerMW: 5000, minCost: 100000, maxCost: 2000000, notes: 'Facilities study deposit' },
    { iso: 'CAISO', phase: 'Phase_4', costPerMW: 10000, minCost: 500000, maxCost: 5000000, notes: 'Network upgrade security' },
    { iso: 'MISO', phase: 'Phase_3', costPerMW: 3000, minCost: 100000, maxCost: 1500000, notes: 'GIA security deposit' },
    { iso: 'ERCOT', phase: 'Phase_3', costPerMW: 4000, minCost: 75000, maxCost: 1000000, notes: 'IA security' },
    { iso: 'PJM', phase: 'Phase_3', costPerMW: 6000, minCost: 100000, maxCost: 3000000, notes: 'Interconnection construction' },
    { iso: 'SPP', phase: 'Phase_2', costPerMW: 3500, minCost: 50000, maxCost: 1500000, notes: 'Facilities study' },
  ]);

  // Timeline Milestones
  const [timelineMilestones, setTimelineMilestones] = useState([
    { iso: 'CAISO', phase: 'Phase_1', typicalDurationDays: 45, criticalPath: 'No', withdrawalNoticeRequired: 10 },
    { iso: 'CAISO', phase: 'Phase_2', typicalDurationDays: 180, criticalPath: 'Yes', withdrawalNoticeRequired: 30 },
    { iso: 'CAISO', phase: 'Phase_3', typicalDurationDays: 365, criticalPath: 'Yes', withdrawalNoticeRequired: 60 },
    { iso: 'MISO', phase: 'Phase_1', typicalDurationDays: 90, criticalPath: 'No', withdrawalNoticeRequired: 15 },
    { iso: 'MISO', phase: 'Phase_2', typicalDurationDays: 270, criticalPath: 'Yes', withdrawalNoticeRequired: 45 },
    { iso: 'ERCOT', phase: 'Phase_1', typicalDurationDays: 60, criticalPath: 'No', withdrawalNoticeRequired: 10 },
    { iso: 'ERCOT', phase: 'Phase_2', typicalDurationDays: 180, criticalPath: 'Yes', withdrawalNoticeRequired: 30 },
    { iso: 'PJM', phase: 'Phase_1', typicalDurationDays: 90, criticalPath: 'No', withdrawalNoticeRequired: 15 },
    { iso: 'PJM', phase: 'Phase_2', typicalDurationDays: 240, criticalPath: 'Yes', withdrawalNoticeRequired: 45 },
  ]);

  // Memoize to avoid reconstructing on every render
  const sheets = useMemo(() => ({
    'ISO_Tariffs': { data: isoTariffs, setter: setIsoTariffs },
    'Projects': { data: projects, setter: setProjects },
    'Cost_Categories': { data: costCategories, setter: setCostCategories },
    'Custom_Rules': { data: customRules, setter: setCustomRules },
    'MW_Based_Costs': { data: mwBasedCosts, setter: setMwBasedCosts },
    'Timeline_Milestones': { data: timelineMilestones, setter: setTimelineMilestones },
  }), [isoTariffs, projects, costCategories, customRules, mwBasedCosts, timelineMilestones]);

  const currentData = sheets[activeSheet].data;

  const exportToCSV = (sheetName) => {
    if (typeof window === 'undefined') return;
    const data = sheets[sheetName].data;
    if (data.length === 0) return;

    const headers = Object.keys(data[0]);
    const csvContent = [
      headers.join(','),
      ...data.map(row =>
        headers.map(h => csvEscape(row[h])).join(',')
      ),
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${sheetName}.csv`;
    a.click();
    // Release the object URL to avoid memory leaks
    window.URL.revokeObjectURL(url);
  };

  const exportAllSheets = () => {
    // Stagger each download so the browser processes them individually
    Object.keys(sheets).forEach((sheetName, index) => {
      setTimeout(() => exportToCSV(sheetName), index * 300);
    });
  };

  // Derive a readable column label from a camelCase or snake_case key
  const formatHeader = (key) => {
    return key
      .replace(/_/g, ' ')
      .replace(/([A-Z])/g, ' $1')
      .replace(/\bPct\b/g, '%')
      .replace(/\bMw\b/g, 'MW')
      .replace(/\bIso\b/g, 'ISO')
      .trim();
  };

  // Derive a stable row key from the most discriminating fields available
  const rowKey = (row, index) => {
    if (row.projectId) return row.projectId;
    if (row.iso && row.phase) return `${row.iso}-${row.phase}`;
    if (row.category) return row.category;
    if (row.iso && row.projectType) return `${row.iso}-${row.projectType}`;
    return index;
  };

  return (
    <div className="w-full h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <div className="bg-green-700 text-white p-4 shadow-lg">
        <h1 className="text-2xl font-bold">Renewable Energy Withdrawal Exposure Master Data</h1>
        <p className="text-sm text-green-100 mt-1">Interconnection, Transmission, Land & Financial Exposure Tracking</p>
      </div>

      {/* Sheet Tabs */}
      <div className="bg-white border-b flex items-center justify-between px-4">
        <div
          role="tablist"
          aria-label="Data sheets"
          className="flex space-x-1 overflow-x-auto py-2"
        >
          {Object.keys(sheets).map(sheet => (
            <button
              key={sheet}
              role="tab"
              aria-selected={activeSheet === sheet}
              onClick={() => setActiveSheet(sheet)}
              className={`px-4 py-2 text-sm font-medium rounded-t transition-colors whitespace-nowrap ${
                activeSheet === sheet
                  ? 'bg-green-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {sheet.replace(/_/g, ' ')}
            </button>
          ))}
        </div>
        <button
          onClick={exportAllSheets}
          className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors ml-4"
        >
          <Download size={16} />
          <span className="text-sm font-medium">Export All CSVs</span>
        </button>
      </div>

      {/* Table Container */}
      <div className="flex-1 overflow-auto p-4">
        <div className="bg-white rounded-lg shadow-md overflow-hidden">
          <div className="overflow-x-auto">
            <table
              className="w-full text-sm"
              aria-label={`${activeSheet.replace(/_/g, ' ')} data`}
            >
              <thead className="bg-gray-100 border-b-2 border-gray-300">
                <tr>
                  {currentData.length > 0 && Object.keys(currentData[0]).map(header => (
                    <th key={header} className="px-4 py-3 text-left font-semibold text-gray-700 whitespace-nowrap">
                      {formatHeader(header)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {currentData.map((row, rowIndex) => (
                  <tr key={rowKey(row, rowIndex)} className="border-b hover:bg-gray-50">
                    {Object.entries(row).map(([key, value], colIndex) => (
                      <td key={`${key}-${colIndex}`} className="px-4 py-3 whitespace-nowrap">
                        {typeof value === 'number' && value > 999
                          ? value.toLocaleString()
                          : String(value)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Instructions */}
        <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h3 className="font-bold text-blue-900 mb-2">Instructions</h3>
          <ul className="text-sm text-blue-800 space-y-1">
            <li><strong>ISO Tariffs:</strong> Core rules per ISO/phase - deposit amounts, penalty percentages, refund policies</li>
            <li><strong>Projects:</strong> Active project portfolio with current phase, costs paid, and milestone dates</li>
            <li><strong>Cost Categories:</strong> Recoverability rules for different expense types based on timing</li>
            <li><strong>Custom Rules:</strong> Exception handling for special cases (storage, offshore wind, etc.)</li>
            <li><strong>MW Based Costs:</strong> Variable costs that scale with project size ($/MW formulas)</li>
            <li><strong>Timeline Milestones:</strong> Typical phase durations and required withdrawal notice periods</li>
          </ul>
          <div className="mt-3 pt-3 border-t border-blue-300">
            <p className="text-sm text-blue-900"><strong>Usage:</strong> Export CSVs &rarr; Import to Excel &rarr; Reference from ExcelDNA UDFs &rarr; Calculate exposure</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ExposureDataWorkbook;
