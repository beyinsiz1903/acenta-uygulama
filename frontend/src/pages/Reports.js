import { useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import Layout from '@/components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { 
  FileText, 
  Download, 
  Calendar,
  TrendingUp,
  DollarSign,
  Users,
  Building,
  FileSpreadsheet
} from 'lucide-react';

const Reports = ({ user, tenant, onLogout }) => {
  const [loading, setLoading] = useState(false);
  const [startDate, setStartDate] = useState(new Date(new Date().setMonth(new Date().getMonth() - 1)).toISOString().split('T')[0]);
  const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);

  const reportCategories = [
    {
      title: 'Financial Reports',
      icon: DollarSign,
      reports: [
        { 
          name: 'Daily Flash Report', 
          endpoint: '/reports/daily-flash/excel',
          hasDateRange: false,
          needsParams: false
        },
        { 
          name: 'Company Aging Report', 
          endpoint: '/reports/company-aging/excel',
          hasDateRange: false,
          needsParams: false
        }
      ]
    },
    {
      title: 'Operational Reports',
      icon: Building,
      reports: [
        { 
          name: 'Housekeeping Efficiency', 
          endpoint: '/reports/housekeeping-efficiency/excel',
          hasDateRange: true,
          needsParams: true
        }
      ]
    },
    {
      title: 'Market Reports',
      icon: TrendingUp,
      reports: [
        { 
          name: 'Market Segment Analysis', 
          endpoint: '/reports/market-segment/excel',
          hasDateRange: true,
          needsParams: true
        }
      ]
    }
  ];

  const handleDownloadReport = async (report) => {
    setLoading(true);
    try {
      let url = report.endpoint;
      
      // Add date parameters if needed
      if (report.needsParams) {
        url += `?start_date=${startDate}&end_date=${endDate}`;
      }
      
      const response = await axios.get(url, {
        responseType: 'blob'
      });
      
      // Create download link
      const blob = new Blob([response.data], { 
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' 
      });
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      
      // Get filename from content-disposition header or use default
      const contentDisposition = response.headers['content-disposition'];
      let filename = `${report.name.replace(/\s+/g, '_')}.xlsx`;
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1].replace(/['"]/g, '');
        }
      }
      
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
      
      toast.success(`${report.name} downloaded successfully!`);
    } catch (error) {
      console.error('Failed to download report:', error);
      toast.error('Failed to download report. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout user={user} tenant={tenant} onLogout={onLogout} currentModule="reports">
      <div className="p-6 max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            <FileSpreadsheet className="inline-block w-8 h-8 mr-2 text-green-600" />
            Reports - Excel Export
          </h1>
          <p className="text-gray-600">Download comprehensive reports in Excel format</p>
        </div>

        {/* Date Range Selector */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calendar className="w-5 h-5 text-blue-600" />
              Date Range (for reports that need dates)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label>Start Date</Label>
                <Input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="mt-1"
                />
              </div>
              <div>
                <Label>End Date</Label>
                <Input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="mt-1"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
          {reportCategories.map((category, idx) => (
            <Card key={idx} className="hover:shadow-lg transition-shadow">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <category.icon className="w-5 h-5 text-blue-600" />
                  {category.title}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {category.reports.map((report, reportIdx) => (
                    <div 
                      key={reportIdx}
                      className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                    >
                      <div className="flex items-center gap-2">
                        <FileText className="w-4 h-4 text-gray-500" />
                        <span className="text-sm font-medium text-gray-700">
                          {report.name}
                        </span>
                      </div>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleDownloadReport(report)}
                        disabled={loading}
                        className="h-8"
                      >
                        <Download className="w-4 h-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        <Card className="mt-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calendar className="w-5 h-5 text-blue-600" />
              Scheduled Reports
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-600 text-sm">
              Configure automatic report generation and email delivery
            </p>
            <Button className="mt-4" variant="outline">
              Configure Schedule
            </Button>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
};

export default Reports;
