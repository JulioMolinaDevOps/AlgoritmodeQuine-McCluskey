from flask import Flask, render_template_string, request, jsonify
import itertools

app = Flask(__name__)

class QuineMcCluskey:
    def __init__(self, minterms, dont_cares=None):
        self.minterms = minterms
        self.dont_cares = dont_cares if dont_cares else []
        self.all_terms = sorted(minterms + self.dont_cares)
        self.num_vars = len(bin(max(self.all_terms))) - 2 if self.all_terms else 1
        self.steps = []
        
    def decimal_to_binary(self, num):
        return bin(num)[2:].zfill(self.num_vars)
    
    def count_ones(self, binary_str):
        return binary_str.count('1')
    
    def can_combine(self, term1, term2):
        diff_count = 0
        diff_pos = -1
        for i in range(len(term1)):
            if term1[i] != term2[i]:
                if term1[i] == '-' or term2[i] == '-':
                    return False, -1
                diff_count += 1
                diff_pos = i
        return diff_count == 1, diff_pos
    
    def combine_terms(self, term1, term2, pos):
        new_term = list(term1)
        new_term[pos] = '-'
        return ''.join(new_term)
    
    def group_by_ones(self, terms_dict):
        groups = {}
        for term, decimals in terms_dict.items():
            ones = self.count_ones(term)
            if ones not in groups:
                groups[ones] = []
            groups[ones].append((term, decimals))
        return dict(sorted(groups.items()))
    
    def find_prime_implicants(self):
        # Paso 1: Convertir minterms a binario y agrupar
        initial_terms = {}
        for term in self.all_terms:
            binary = self.decimal_to_binary(term)
            initial_terms[binary] = [term]
        
        groups = self.group_by_ones(initial_terms)
        self.steps.append({
            'title': 'Paso 1: Agrupación inicial por número de 1s',
            'groups': groups,
            'description': 'Términos agrupados según la cantidad de 1s en su representación binaria',
            'show_binary': True  # Mostrar binario en el paso 1
        })
        
        # Pasos siguientes: Combinar términos
        step_num = 2
        all_prime_implicants = set()
        
        while True:
            new_terms = {}
            used_terms = set()
            combined_any = False
            
            group_keys = sorted(groups.keys())
            for i in range(len(group_keys) - 1):
                current_group = groups[group_keys[i]]
                next_group = groups[group_keys[i + 1]]
                
                for term1, dec1 in current_group:
                    for term2, dec2 in next_group:
                        can_comb, pos = self.can_combine(term1, term2)
                        if can_comb:
                            new_term = self.combine_terms(term1, term2, pos)
                            combined_decimals = sorted(list(set(dec1 + dec2)))
                            
                            if new_term not in new_terms:
                                new_terms[new_term] = combined_decimals
                            
                            used_terms.add(term1)
                            used_terms.add(term2)
                            combined_any = True
            
            # Identificar implicantes primos (términos no combinados)
            for group_terms in groups.values():
                for t, d in group_terms:
                    if t not in used_terms:
                        # Solo agregar minterms originales, no don't cares
                        original_minterms = [x for x in d if x in self.minterms]
                        if original_minterms:
                            all_prime_implicants.add((t, tuple(d)))
            
            if not combined_any:
                break
            
            groups = self.group_by_ones(new_terms)
            self.steps.append({
                'title': f'Paso {step_num}: Combinación de términos',
                'groups': groups,
                'description': f'Términos combinados que difieren en un solo bit',
                'used_terms': list(used_terms),
                'show_binary': False  # Mostrar números naturales desde paso 2
            })
            step_num += 1
        
        # Último grupo también son implicantes primos
        for group_terms in groups.values():
            for t, d in group_terms:
                original_minterms = [x for x in d if x in self.minterms]
                if original_minterms:
                    all_prime_implicants.add((t, tuple(d)))
        
        return list(all_prime_implicants)
    
    def find_essential_prime_implicants(self, prime_implicants):
        # Crear tabla de cobertura
        coverage = {}
        for minterm in self.minterms:
            coverage[minterm] = []
            for impl, decimals in prime_implicants:
                if minterm in decimals:
                    coverage[minterm].append((impl, decimals))
        
        # Crear matriz de cobertura para visualización
        coverage_matrix = {}
        for impl, decimals in prime_implicants:
            coverage_matrix[impl] = {
                'decimals': decimals,
                'covers': [m for m in self.minterms if m in decimals]
            }
        
        self.steps.append({
            'title': f'Paso {len(self.steps) + 1}: Tabla de Cobertura',
            'coverage': coverage,
            'coverage_matrix': coverage_matrix,
            'prime_implicants': prime_implicants,
            'description': 'Tabla que muestra qué implicantes primos cubren cada minterm'
        })
        
        # Encontrar implicantes esenciales
        essential = []
        covered_minterms = set()
        essential_impls = set()
        
        for minterm, impls in coverage.items():
            if len(impls) == 1:
                impl = impls[0]
                if impl not in essential:
                    essential.append(impl)
                    essential_impls.add(impl[0])
                    covered_minterms.update(impl[1])
        
        self.steps.append({
            'title': f'Paso {len(self.steps) + 1}: Implicantes Primos Esenciales',
            'essential': essential,
            'essential_impls': list(essential_impls),
            'covered': list(covered_minterms),
            'description': 'Implicantes que son los únicos que cubren ciertos minterms'
        })
        
        return essential, covered_minterms
    
    def implicant_to_expression(self, implicant):
        variables = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'][:self.num_vars]
        terms = []
        for i, bit in enumerate(implicant):
            if bit == '1':
                terms.append(variables[i])
            elif bit == '0':
                terms.append(variables[i] + "'")
        return ''.join(terms) if terms else '1'
    
    def binary_to_difference(self, binary):
        """Convierte binario con guiones a números naturales que representan las diferencias"""
        differences = []
        for i, bit in enumerate(binary):
            if bit == '-':
                # Calcula la potencia de 2 correspondiente a esa posición
                power = self.num_vars - i - 1
                differences.append(str(2 ** power))
        return ','.join(differences) if differences else binary
    
    def solve(self):
        prime_implicants = self.find_prime_implicants()
        essential, covered = self.find_essential_prime_implicants(prime_implicants)
        
        # Expresión final
        expression_terms = [self.implicant_to_expression(impl[0]) for impl in essential]
        final_expression = ' + '.join(expression_terms)
        
        self.steps.append({
            'title': f'Paso {len(self.steps) + 1}: Expresión Lógica Simplificada',
            'expression': final_expression,
            'description': 'Función booleana simplificada en forma de suma de productos'
        })
        
        return {
            'prime_implicants': prime_implicants,
            'essential_implicants': essential,
            'expression': final_expression,
            'steps': self.steps
        }

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Algoritmo Quine-McCluskey</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #5e72e4 0%, #825ee4 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .input-section {
            padding: 30px;
            background: #f8f9fa;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-group label {
            display: block;
            font-weight: 600;
            margin-bottom: 8px;
            color: #333;
            font-size: 1.1em;
        }
        
        .form-group input {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 1em;
            transition: border-color 0.3s;
        }
        
        .form-group input:focus {
            outline: none;
            border-color: #5e72e4;
        }
        
        .help-text {
            font-size: 0.9em;
            color: #666;
            margin-top: 5px;
        }
        
        .btn {
            background: linear-gradient(135deg, #5e72e4 0%, #825ee4 100%);
            color: white;
            border: none;
            padding: 15px 40px;
            font-size: 1.1em;
            border-radius: 8px;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            font-weight: 600;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(94, 114, 228, 0.4);
        }
        
        .btn:active {
            transform: translateY(0);
        }
        
        .results {
            padding: 30px;
            display: none;
        }
        
        .step {
            background: #f8f9fa;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 10px;
            border-left: 4px solid #5e72e4;
        }
        
        .step-title {
            font-size: 1.4em;
            color: #5e72e4;
            margin-bottom: 10px;
            font-weight: 600;
        }
        
        .step-description {
            color: #666;
            margin-bottom: 15px;
            font-style: italic;
        }
        
        .group {
            background: white;
            padding: 15px;
            margin: 10px 0;
            border-radius: 8px;
            border: 1px solid #ddd;
        }
        
        .group-header {
            font-weight: 600;
            color: #333;
            margin-bottom: 10px;
            font-size: 1.1em;
        }
        
        .term {
            display: inline-block;
            background: #e3f2fd;
            padding: 8px 15px;
            margin: 5px;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
            font-size: 1em;
        }
        
        .term-binary {
            font-weight: 600;
            color: #1976d2;
        }
        
        .term-decimal {
            color: #666;
            font-size: 0.9em;
        }
        
        .final-expression {
            background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
            padding: 25px;
            border-radius: 10px;
            text-align: center;
            font-size: 1.5em;
            font-weight: 600;
            color: #1a1a1a;
            margin-top: 20px;
            font-family: 'Courier New', monospace;
        }
        
        .loading {
            text-align: center;
            padding: 20px;
            display: none;
        }
        
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #5e72e4;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .coverage-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
            font-size: 0.95em;
        }
        
        .table-wrapper {
            overflow-x: auto;
            overflow-y: auto;   /* <- scroll vertical habilitado */
            max-width: 100%;
            max-height: 400px;  /* <- altura máxima antes de scroll vertical */
            border: 2px solid #333;
            border-radius: 8px;
            margin-top: 15px;
        }
        
        .table-wrapper::-webkit-scrollbar {
            height: 12px;
            width: 12px;
        }
        
        .table-wrapper::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 10px;
        }
        
        .table-wrapper::-webkit-scrollbar-thumb {
            background: #5e72e4;
            border-radius: 10px;
        }
        
        .coverage-table th,
        .coverage-table td {
            padding: 12px 8px;
            border: 2px solid #333;
            text-align: center;
            min-width: 45px;
            white-space: nowrap;
        }
        
        .coverage-table th {
            background: #2c3e50;
            color: white;
            font-weight: 600;
            font-size: 1em;
            position: sticky;
            top: 0;
            z-index: 10;
        }
        
        .coverage-table .impl-cell {
            background: #d4a574;
            font-weight: 600;
            text-align: left;
            padding-left: 15px;
            font-family: 'Courier New', monospace;
            position: sticky;
            left: 0;
            z-index: 5;
            min-width: 150px;
        }
        
        .coverage-table .covered-cell {
            background: white;
            position: relative;
        }
        
        .coverage-table .covered-cell.has-cover::after {
            content: '✖';
            color: #3498db;
            font-size: 1.8em;
            font-weight: bold;
        }
        
        .coverage-table .essential-star {
            color: #27ae60;
            font-size: 1.5em;
            margin-right: 8px;
        }
        
        .coverage-table tr:hover .covered-cell {
            background: #ecf0f1;
        }
        
        .essential-badge {
            background: #43e97b;
            color: #1a1a1a;
            padding: 5px 10px;
            border-radius: 5px;
            font-size: 0.9em;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔬 Algoritmo de Quine-McCluskey</h1>
            <p>Simplificación de Funciones Lógicas Digitales</p>
        </div>
        
        <div class="input-section">
            <form id="qmForm">
                <div class="form-group">
                    <label for="minterms">Mintérminos (separados por comas):</label>
                    <input type="text" id="minterms" name="minterms" placeholder="Ejemplo: 0,1,2,5,6,7" required>
                    <div class="help-text">Ingrese los números decimales de los mintérminos de su función lógica</div>
                </div>
                
                <div class="form-group">
                    <label for="dontcares">Don't Cares - Opcional (separados por comas):</label>
                    <input type="text" id="dontcares" name="dontcares" placeholder="Ejemplo: 3,4">
                    <div class="help-text">Términos que pueden ser 0 o 1 (opcional)</div>
                </div>
                
                <button type="submit" class="btn">Calcular Simplificación</button>
            </form>
        </div>
        
        <div class="loading">
            <div class="spinner"></div>
            <p>Procesando...</p>
        </div>
        
        <div class="results" id="results"></div>
    </div>
    
    <script>
        function getBinaryDifference(binary) {
            // Si no tiene guiones, devolver el binario original
            if (!binary.includes('-')) {
                return binary;
            }
            
            // Calcular las posiciones de los guiones como números naturales
            const numVars = binary.length;
            const differences = [];
            
            for (let i = 0; i < binary.length; i++) {
                if (binary[i] === '-') {
                    const power = numVars - i - 1;
                    differences.push(Math.pow(2, power));
                }
            }
            
            return differences.join(',');
        }
        
        document.getElementById('qmForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const minterms = document.getElementById('minterms').value;
            const dontcares = document.getElementById('dontcares').value;
            
            document.querySelector('.loading').style.display = 'block';
            document.getElementById('results').style.display = 'none';
            
            try {
                const response = await fetch('/calculate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        minterms: minterms,
                        dontcares: dontcares
                    })
                });
                
                const data = await response.json();
                
                if (data.error) {
                    alert('Error: ' + data.error);
                    return;
                }
                
                displayResults(data);
            } catch (error) {
                alert('Error al procesar: ' + error.message);
            } finally {
                document.querySelector('.loading').style.display = 'none';
            }
        });
        
        function displayResults(data) {
            const resultsDiv = document.getElementById('results');
            let html = '';
            
            data.steps.forEach((step, index) => {
                html += `<div class="step">
                    <div class="step-title">${step.title}</div>
                    <div class="step-description">${step.description}</div>`;                
                
                if (step.groups) {
                    for (const [ones, terms] of Object.entries(step.groups)) {
                        html += `<div class="group">
                            <div class="group-header">Grupo ${ones} (${ones} uno${ones != 1 ? 's' : ''})</div>`;                        
                        terms.forEach(([binary, decimals]) => {
                            // Mostrar binario en paso 1, números naturales desde paso 2
                            const display = step.show_binary ? binary : getBinaryDifference(binary);
                            html += `<div class="term">
                                <span class="term-binary">${display}</span>
                                <span class="term-decimal"> → (${decimals.join(', ')})</span>
                            </div>`;                        
                        });                        
                        html += `</div>`;
                    }
                }
                
                if (step.coverage_matrix) {
                    // Obtener todos los minterms ordenados
                    const allMinterms = Object.keys(step.coverage).map(Number).sort((a, b) => a - b);
                    const impls = Object.keys(step.coverage_matrix);
                    
                    html += `<div class="table-wrapper"><table class="coverage-table">
                        <thead>
                            <tr>
                                <th style="background: #34495e;">Implicante</th>`;                    
                    allMinterms.forEach(minterm => {
                        html += `<th>${minterm}</th>`;
                    });                    
                    html += `</tr></thead><tbody>`;                    
                    impls.forEach(impl => {
                        const data = step.coverage_matrix[impl];
                        const displayImpl = getBinaryDifference(impl);
                        html += `<tr>
                            <td class="impl-cell">${displayImpl}</td>`;                        
                        allMinterms.forEach(minterm => {
                            const isCovered = data.covers.includes(minterm);
                            html += `<td class="covered-cell ${isCovered ? 'has-cover' : ''}"></td>`;
                        });                        
                        html += `</tr>`;
                    });                    
                    html += `</tbody></table></div>`;
                }
                
                if (step.coverage && !step.coverage_matrix) {
                    html += `<div class="table-wrapper"><table class="coverage-table">
                        <thead>
                            <tr>
                                <th>Minterm</th>
                                <th>Implicantes Primos que lo cubren</th>
                            </tr>
                        </thead>
                        <tbody>`;                    
                    for (const [minterm, impls] of Object.entries(step.coverage)) {
                        html += `<tr>
                            <td>${minterm}</td>
                            <td>`;                        
                        impls.forEach(([impl, decs]) => {
                            const diff = getBinaryDifference(impl);
                            html += `<span class="term">${diff}</span> `;
                        });
                        html += `</td></tr>`;
                    }                    
                    html += `</tbody></table></div>`;
                }
                
                if (step.essential) {
                    html += `<div class="group">`;
                    step.essential.forEach(([impl, decs]) => {
                        const diff = getBinaryDifference(impl);
                        html += `<span class="term">
                            <span class="essential-badge">ESENCIAL</span>
                            <span class="term-binary">${diff}</span>
                            <span class="term-decimal"> → (${decs.join(', ')})</span>
                        </span>`;
                    });
                    html += `</div>`;
                }
                
                if (step.expression) {
                    html += `<div class="final-expression">
                        F = ${step.expression}
                    </div>`;
                }
                
                html += `</div>`;
            });
            
            resultsDiv.innerHTML = html;
            resultsDiv.style.display = 'block';
            resultsDiv.scrollIntoView({ behavior: 'smooth' });
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        data = request.json
        
        # Parsear minterms
        minterms_str = data.get('minterms', '')
        minterms = [int(x.strip()) for x in minterms_str.split(',') if x.strip()]
        
        # Parsear don't cares
        dontcares_str = data.get('dontcares', '')
        dontcares = [int(x.strip()) for x in dontcares_str.split(',') if x.strip()] if dontcares_str else []
        
        if not minterms:
            return jsonify({'error': 'Debe ingresar al menos un mintérmino'})
        
        # Ejecutar algoritmo
        qm = QuineMcCluskey(minterms, dontcares)
        result = qm.solve()
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)