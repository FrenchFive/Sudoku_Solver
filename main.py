import os
import time
import multiprocessing
from multiprocessing import Manager
import threading
import http.server
import urllib.parse
import json
try:
    from tqdm import tqdm
except ImportError:  # Fallback when tqdm is unavailable
    class tqdm:
        def __init__(self, iterable=None, total=None, **kwargs):
            self.n = 0
            self.total = total
        def update(self, n=1):
            self.n += n
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

def run_server(shared_state):
    import http.server
    import os
    import threading
    import json
    import urllib.parse

    script_dir = os.path.dirname(os.path.abspath(__file__))

    class SudokuHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/' or self.path == '/index.html':
                # Read index.html
                index_path = os.path.join(script_dir, 'index.html')
                try:
                    with open(index_path, 'r', encoding='utf-8') as f:
                        html = f.read()
                except FileNotFoundError:
                    self.send_error(404, "File not found.")
                    return
                # Generate table rows
                table_rows = ''
                grid = shared_state['grid']
                for i in range(9):
                    table_rows += '<tr>'
                    for j in range(9):
                        value = grid[i][j] if grid[i][j] != 0 else ''
                        table_rows += '<td><input type="text" name="cell_{}_{}" value="{}" maxlength="1" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false"></td>'.format(i, j, value)
                    table_rows += '</tr>'
                # Replace placeholder
                html = html.replace('{table_rows}', table_rows)
                # Send response
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(html.encode('utf-8'))
            elif self.path == '/solution':
                if shared_state.get('solution', None):
                    # Send solution as JSON
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    response = {
                        'solution': shared_state['solution'],
                        'original': shared_state['grid'],
                        'steps': shared_state.get('steps', [])
                    }
                    self.wfile.write(json.dumps(response).encode('utf-8'))
                else:
                    # Solution not ready
                    self.send_response(204)  # No Content
                    self.end_headers()
            else:
                # Serve static files
                return http.server.SimpleHTTPRequestHandler.do_GET(self)

        def do_POST(self):
            if self.path == '/simulate':
                threading.Thread(target=start_simulation, args=(shared_state,), daemon=True).start()
                self.send_response(200)
                self.end_headers()
                return
            if self.path == '/clear':
                grid = [[0] * 9 for _ in range(9)]
                shared_state['grid'] = grid
                shared_state['solution'] = None
                shared_state['input_received'] = False
                shared_state['steps'] = []
                save_path = os.path.join(script_dir, 'sudoku_save.txt')
                with open(save_path, 'w') as f:
                    for _ in range(9):
                        f.write('0 0 0 0 0 0 0 0 0\n')
                steps_path = os.path.join(script_dir, 'sudoku_steps.txt')
                with open(steps_path, 'w') as f:
                    pass
                self.send_response(200)
                self.end_headers()
                return

            # Process form data
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            # Parse form data
            parsed_data = urllib.parse.parse_qs(post_data.decode('utf-8'))
            # Update grid
            grid = [[0]*9 for _ in range(9)]
            for i in range(9):
                for j in range(9):
                    cell_name = 'cell_{}_{}'.format(i, j)
                    value = parsed_data.get(cell_name, [''])[0]
                    try:
                        num = int(value)
                        if 1 <= num <= 9:
                            grid[i][j] = num
                        else:
                            grid[i][j] = 0
                    except ValueError:
                        grid[i][j] = 0
            # Save grid to shared_state
            shared_state['grid'] = grid
            shared_state['input_received'] = True
            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            # Read index.html
            index_path = os.path.join(script_dir, 'index.html')
            try:
                with open(index_path, 'r', encoding='utf-8') as f:
                    html = f.read()
            except FileNotFoundError:
                    self.send_error(404, "File not found.")
                    return
            # Generate table rows
            table_rows = ''
            for i in range(9):
                table_rows += '<tr>'
                for j in range(9):
                    value = grid[i][j] if grid[i][j] != 0 else ''
                    table_rows += '<td><input type="text" name="cell_{}_{}" value="{}" maxlength="1" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false"></td>'.format(i, j, value)
                table_rows += '</tr>'
            # Replace placeholder
            html = html.replace('{table_rows}', table_rows)
            # Send response
            self.wfile.write(html.encode('utf-8'))

    # Try to find an available port
    for port in range(8000, 9000):
        try:
            server_address = ('', port)
            httpd = http.server.HTTPServer(server_address, SudokuHTTPRequestHandler)
            shared_state['port'] = port
            break
        except OSError as e:
            if e.errno == 98:  # Address already in use
                continue
            else:
                raise
    else:
        print("No available port found between 8000 and 9000.")
        shared_state['server_failed'] = True
        return

    # Run the server
    httpd.serve_forever()

def print_grid(grid):
    for i in range(9):
        if i % 3 == 0 and i != 0:
            print("-"*21)
        for j in range(9):
            if j % 3 == 0 and j != 0:
                print("| ", end='')
            print(str(grid[i][j]) if grid[i][j] != 0 else '.', end=' ')
        print()

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def find_empty_cell(grid):
    for i in range(9):
        for j in range(9):
            if grid[i][j] == 0:
                return i, j
    return None

def find_best_cell(grid):
    best_cell = None
    best_options = None
    min_options = 10
    for i in range(9):
        for j in range(9):
            if grid[i][j] == 0:
                options = get_possible_numbers(grid, i, j)
                if len(options) < min_options:
                    min_options = len(options)
                    best_cell = (i, j)
                    best_options = options
                    if min_options == 1:
                        return best_cell + (best_options,)
    if best_cell is None:
        return None
    return best_cell + (best_options,)

def is_valid(grid, row, col, num):
    # Check row
    if num in grid[row]:
        return False
    # Check column
    if num in (grid[i][col] for i in range(9)):
        return False
    # Check box
    start_row = row - row % 3
    start_col = col - col % 3
    for i in range(3):
        for j in range(3):
            if grid[start_row + i][start_col + j] == num:
                return False
    return True

def get_possible_numbers(grid, row, col):
    numbers = set(range(1, 10))
    numbers -= set(grid[row])  # Remove numbers present in the row
    numbers -= set(grid[i][col] for i in range(9))  # Remove numbers present in the column
    start_row = row - row % 3
    start_col = col - col % 3
    # Remove numbers present in the 3x3 box
    numbers -= set(
        grid[start_row + i][start_col + j]
        for i in range(3) for j in range(3)
    )
    return numbers

def count_constraints(grid, row, col, num):
    count = 0
    for i in range(9):
        if grid[row][i] == 0:
            count += 1
        if grid[i][col] == 0:
            count += 1
    start_row = row - row % 3
    start_col = col - col % 3
    for i in range(3):
        for j in range(3):
            if grid[start_row + i][start_col + j] == 0:
                count += 1
    return count

def count_filled(grid):
    return sum(1 for r in grid for c in r if c != 0)

def solve_sudoku_steps(grid, steps, step_file, pbar=None, stats=None):
    """Recursively solve sudoku while recording each step."""
    best = find_best_cell(grid)
    if not best:
        return True
    row, col, possible_numbers = best
    possible_numbers = sorted(possible_numbers, key=lambda n: count_constraints(grid, row, col, n))
    for num in possible_numbers:
        if is_valid(grid, row, col, num):
            grid[row][col] = num
            if stats is not None:
                stats['trials'] += 1
            if pbar is not None:
                filled = count_filled(grid)
                if filled > pbar.n:
                    pbar.update(filled - pbar.n)
            snapshot = [r[:] for r in grid]
            steps.append(snapshot)
            for r in snapshot:
                step_file.write(" ".join(map(str, r)) + "\n")
            step_file.write("\n")
            if solve_sudoku_steps(grid, steps, step_file, pbar, stats):
                return True
            grid[row][col] = 0
            if pbar is not None:
                filled = count_filled(grid)
                if filled > pbar.n:
                    pbar.update(filled - pbar.n)
            snapshot = [r[:] for r in grid]
            steps.append(snapshot)
            for r in snapshot:
                step_file.write(" ".join(map(str, r)) + "\n")
            step_file.write("\n")
    return False

def solve_sudoku(grid, queue=None, progress=None, worker_id=None, stop_event=None, stats=None):
    if stop_event and stop_event.is_set():
        return False
    best = find_best_cell(grid)
    if not best:
        return True
    row, col, possible_numbers = best
    if not possible_numbers:
        if stats is not None:
            stats['backtracks'] += 1
        return False
    possible_numbers = sorted(possible_numbers, key=lambda num: count_constraints(grid, row, col, num))
    for num in possible_numbers:
        if stop_event and stop_event.is_set():
            return False
        if is_valid(grid, row, col, num):
            grid[row][col] = num
            if stats is not None:
                stats['attempts'] += 1
            if progress is not None:
                progress['grid'] = [row[:] for row in grid]
            if solve_sudoku(grid, queue, progress, worker_id, stop_event, stats):
                if queue and queue.empty():
                    queue.put([row[:] for row in grid])
                return True
            grid[row][col] = 0
            if stats is not None:
                stats['backtracks'] += 1
    return False

def worker(grid, queue, progress, worker_id, stop_event, stats, initial_cell):
    grid_copy = [row[:] for row in grid]
    row, col, possible_numbers = initial_cell
    possible_numbers = sorted(possible_numbers, key=lambda num: count_constraints(grid_copy, row, col, num))
    for num in possible_numbers:
        if stop_event.is_set():
            break
        if is_valid(grid_copy, row, col, num):
            grid_copy[row][col] = num
            if stats is not None:
                stats['attempts'] += 1
            if progress is not None:
                progress['grid'] = [row[:] for row in grid_copy]
            if solve_sudoku(grid_copy, queue, progress, worker_id, stop_event, stats):
                stop_event.set()
                if queue.empty():
                    queue.put([row[:] for row in grid_copy])
                break
            grid_copy[row][col] = 0
            if stats is not None:
                stats['backtracks'] += 1

def display_progress(progress, stop_event):
    while not stop_event.is_set():
        clear_screen()
        print("Solving Sudoku...")
        if 'grid' in progress:
            print_grid(progress['grid'])
        else:
            print("Initializing...")
        time.sleep(0.5)
    clear_screen()
    if 'grid' in progress:
        print("Solved Sudoku:")
        print_grid(progress['grid'])
    else:
        print("No solution found.")

def solve_puzzle(shared_state, save_file):
    """Solve the sudoku in shared_state and store the solution with step tracing."""
    grid = [row[:] for row in shared_state['grid']]
    steps = []
    steps_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sudoku_steps.txt')
    stats = {'trials': 0}

    clear_screen()
    print("Solving the sudoku...")
    time_start = time.time()

    with tqdm(total=81, desc="Solving") as pbar:
        with open(steps_path, 'w') as step_file:
            solved = solve_sudoku_steps(grid, steps, step_file, pbar, stats)

    elapsed_time = time.time() - time_start

    if solved:
        shared_state['solution'] = grid
        with open(save_file, 'w') as f:
            for row in grid:
                f.write(" ".join(map(str, row)) + "\n")
        print("Sudoku solved in {:.2f} seconds after {} trials".format(elapsed_time, stats['trials']))
    else:
        shared_state['solution'] = None
        print("No solution exists.")

    shared_state['steps'] = steps

def start_simulation(shared_state):
    """Use the keyboard module to type the solution in the active window."""
    solution = shared_state.get('solution')
    original = shared_state.get('grid')
    if not solution:
        print("No solution available for simulation.")
        return
    try:
        import keyboard
    except ImportError:
        print("The 'keyboard' module is required for simulation.")
        return

    for r in range(9):
        for c in range(9):
            if original[r][c] == 0:
                keyboard.write(str(solution[r][c]))
            if r == 8 and c == 8:
                return
            if c < 8:
                keyboard.press_and_release('right')
            else:
                keyboard.press_and_release('down')
                for _ in range(8):
                    keyboard.press_and_release('left')

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    save_file = os.path.join(script_dir, "sudoku_save.txt")

    manager = multiprocessing.Manager()
    shared_state = manager.dict()
    shared_state['grid'] = [[0]*9 for _ in range(9)]
    shared_state['solution'] = None
    shared_state['input_received'] = False
    shared_state['server_failed'] = False
    shared_state['port'] = None
    shared_state['steps'] = []

    # Try to load saved grid
    if os.path.exists(save_file):
        with open(save_file, 'r') as f:
            lines = f.readlines()
            if len(lines) == 9:
                grid = [[0]*9 for _ in range(9)]
                for i in range(9):
                    row_values = list(map(int, lines[i].strip().split()))
                    if len(row_values) == 9:
                        grid[i] = row_values
                shared_state['grid'] = grid

    # Start the server process
    server_process = multiprocessing.Process(target=run_server, args=(shared_state,))
    server_process.start()

    # Wait for the server to set the port or fail
    while shared_state['port'] is None and not shared_state['server_failed']:
        time.sleep(0.1)

    if shared_state['server_failed']:
        print("Failed to start the server. Exiting.")
        server_process.terminate()
        server_process.join()
        return

    port = shared_state['port']
    print(f"Please open your web browser and go to http://localhost:{port} to enter the Sudoku.")

    try:
        while True:
            while not shared_state.get('input_received', False):
                time.sleep(0.1)
            shared_state['solution'] = None
            solve_puzzle(shared_state, save_file)
            shared_state['input_received'] = False
            print("Solution ready. You can view it in your browser.")
    except KeyboardInterrupt:
        pass
    finally:
        server_process.terminate()
        server_process.join()
        print("Server stopped.")

if __name__ == "__main__":
    main()
