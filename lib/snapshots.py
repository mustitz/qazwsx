import re


DIGITS = 4
ISNUM = re.compile(f'^[0-9]{{{DIGITS}}}$')


class Snapshots(list):
    def _enumerate(self, parent):
        self.append(parent)
        for child in parent.children:
            self._enumerate(child)

    def populate(self, machine):
        self.clear()

        root = machine.current_snapshot
        if root is None:
            return

        while True:
            parent = root.parent
            if getattr(parent, 'name', None) is None:
                break
            root = parent

        self._enumerate(root)

    def find(self, name):
        if not self:
            return None

        for snapshot in self:
            if snapshot.name == name:
                return snapshot

        alts = []

        prefix = name + '-'
        offset = len(prefix) - 1
        for i, snapshot in enumerate(self):
            if snapshot.name.startswith(prefix):
                suffix = snapshot.name[-offset:]
                if re.match(ISNUM, suffix):
                    alts.append((int(suffix), i))

        if not alts:
            return None

        alts.sort()
        snapshot = self[alts[-1][1]]

        return snapshot

    def next_name(self, name):
        last = self.find(name)
        if last is None:
            return name + '-' + ('0' * DIGITS)
        if last.name == name:
            return None

        offset = len(name) - 1
        suffix = last.name[-offset:]
        num = int(suffix)
        return name + '-' + str(num + 1).rjust(DIGITS, '0')
