import pandas as pd
import numpy as np

class DataAnalyzer:
    def __init__(self, filepath):
        self.df = pd.read_csv(filepath) if filepath.endswith('.csv') else pd.read_excel(filepath)
        # Basic cleanup
        self.df = self.df.dropna(how='all')
    
    def get_summary(self):
        """Returns statistical summary of the dataset."""
        categorical_cols = self.df.select_dtypes(include=['object', 'category']).columns.tolist()
        categorical_values = {col: self.df[col].dropna().unique().tolist() for col in categorical_cols}
        
        summary = {
            'rows': len(self.df),
            'columns': len(self.df.columns),
            'col_names': list(self.df.columns),
            'dtypes': {col: str(dtype) for col, dtype in self.df.dtypes.items()},
            'missing_values': self.df.isnull().sum().to_dict(),
            'stats': self.df.describe(include=[np.number]).to_dict() if not self.df.select_dtypes(include=[np.number]).empty else {},
            'categorical_values': categorical_values
        }
        return summary

    def get_chart_data(self):
        """Generates data for Chart.js based on column types."""
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = self.df.select_dtypes(include=['object', 'category']).columns.tolist()
        
        chart_data = []
        
        # 1. Histogram for first numeric column
        if numeric_cols:
            col = numeric_cols[0]
            counts, bins = np.histogram(self.df[col].dropna(), bins=10)
            chart_data.append({
                'type': 'bar',
                'title': f'Distribution of {col}',
                'labels': [f"{bins[i]:.2f}-{bins[i+1]:.2f}" for i in range(len(bins)-1)],
                'data': counts.tolist()
            })
            
        # 2. Bar chart for first categorical column
        if categorical_cols:
            col = categorical_cols[0]
            top_ten = self.df[col].value_counts().head(6)
            chart_data.append({
                'type': 'bar',
                'title': f'Top Categories in {col}',
                'labels': top_ten.index.tolist(),
                'data': top_ten.values.tolist()
            })
            
        # 3. Scatter plot for first two numeric columns
        if len(numeric_cols) >= 2:
            x, y = numeric_cols[0], numeric_cols[1]
            valid_df = self.df[[x, y]].dropna()
            sample_df = valid_df.sample(min(100, len(valid_df)))
            scatter_points = [{'x': float(row[x]), 'y': float(row[y])} for _, row in sample_df.iterrows()]
            chart_data.append({
                'type': 'scatter',
                'title': f'{x} vs {y}',
                'data': scatter_points,
                'xLabel': x,
                'yLabel': y
            })

        # 4. Line chart for first numeric column trend
        if numeric_cols:
            col = numeric_cols[0]
            sample = self.df[col].dropna().head(50)
            chart_data.append({
                'type': 'line',
                'title': f'Trend of {col}',
                'labels': list(range(1, len(sample) + 1)),
                'data': [float(v) for v in sample.values]
            })
            
        return chart_data

    def clean_data(self, instructions, filepath):
        """Applies data cleaning instructions to the dataframe and saves it."""
        for col, method in instructions.items():
            if col not in self.df.columns:
                continue
                
            if method == 'mean' and pd.api.types.is_numeric_dtype(self.df[col]):
                self.df[col] = self.df[col].fillna(self.df[col].mean())
            elif method == 'median' and pd.api.types.is_numeric_dtype(self.df[col]):
                self.df[col] = self.df[col].fillna(self.df[col].median())
            elif method == 'mode':
                mode_val = self.df[col].mode()
                if not mode_val.empty:
                    self.df[col] = self.df[col].fillna(mode_val[0])
            elif method == 'drop_rows':
                self.df = self.df.dropna(subset=[col])
            elif method == 'drop_column':
                self.df = self.df.drop(columns=[col])
            elif method == 'unknown':
                self.df[col] = self.df[col].fillna("Unknown")
                
        # Save changes back to the file
        if filepath.endswith('.csv'):
            self.df.to_csv(filepath, index=False)
        elif filepath.endswith(('.xls', '.xlsx')):
            self.df.to_excel(filepath, index=False)

