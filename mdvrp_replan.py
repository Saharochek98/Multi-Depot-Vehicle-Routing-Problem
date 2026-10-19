"""Быстрая реконфигурация MDVRP после отмены заказов (relocate + 2-opt)."""
from time import perf_counter


def replan(routes, cancelled, dist, capacity, seconds=1.0):
    """routes: {(склад, автомобиль): [клиенты]}; dist[u][v]: цена дуги u -> v."""
    if capacity < 1 or seconds < 0:
        raise ValueError("capacity должен быть положительным, seconds — неотрицательным")
    clients = [c for route in routes.values() for c in route]
    if len(clients) != len(set(clients)) or any(len(r) > capacity for r in routes.values()):
        raise ValueError("Исходные маршруты нарушают ограничения MDVRP")
    if set(cancelled) - set(clients):
        raise ValueError("Отменённый клиент отсутствует в исходных маршрутах")

    result = {vehicle: [c for c in path if c not in cancelled]
              for vehicle, path in routes.items()}

    def cost(vehicle, path):
        seq = [vehicle[0], *path, vehicle[0]]
        return sum(dist[a][b] for a, b in zip(seq, seq[1:]))

    deadline = perf_counter() + seconds
    while perf_counter() < deadline:
        best_gain, best_change = 1e-10, None
        for va, pa in result.items():
            for i, customer in enumerate(pa):
                shorter = pa[:i] + pa[i + 1:]
                removal = cost(va, pa) - cost(va, shorter)
                for vb, pb in result.items():
                    if va == vb or len(pb) >= capacity:
                        continue
                    for j in range(len(pb) + 1):
                        longer = pb[:j] + [customer] + pb[j:]
                        gain = removal + cost(vb, pb) - cost(vb, longer)
                        if gain > best_gain:
                            best_gain, best_change = gain, {va: shorter, vb: longer}
            # Полный пересчёт стоимости: граф ориентированный.
            for i in range(len(pa)):
                for j in range(i + 2, len(pa) + 1):
                    changed = pa[:i] + pa[i:j][::-1] + pa[j:]
                    gain = cost(va, pa) - cost(va, changed)
                    if gain > best_gain:
                        best_gain, best_change = gain, {va: changed}
        if best_change is None:
            break
        result.update(best_change)

    active = set(clients) - set(cancelled)
    assigned = [c for path in result.values() for c in path]
    assert set(assigned) == active and len(assigned) == len(active)
    assert all(len(path) <= capacity for path in result.values())
    return result, sum(cost(v, p) for v, p in result.items())


if __name__ == "__main__":
    # Пример: два склада (0, 1), по одному автомобилю; клиент 6 отменил заказ.
    coords = {0: (0, 0), 1: (10, 0), 2: (1, 1), 3: (2, 2),
              4: (9, 1), 5: (8, 2), 6: (4, 1)}
    dist = {a: {b: abs(x - xx) + abs(y - yy) + (0.2 if a > b else 0)
                for b, (xx, yy) in coords.items()}
            for a, (x, y) in coords.items()}
    old = {(0, 0): [2, 6, 3], (1, 0): [4, 5]}
    new, total = replan(old, {6}, dist, capacity=3, seconds=0.5)
    print("Маршруты:", new)
    print("Стоимость:", round(total, 2))
