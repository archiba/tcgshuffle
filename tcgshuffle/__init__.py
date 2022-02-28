from random import Random
from typing import List
from tqdm import tqdm
import numpy

__version__ = '0.1.1'


class Card:
    pos: int

    def __init__(self, pos: int):
        self.pos = pos

    def __str__(self):
        return f"Card({self.pos})"

    def __repr__(self):
        return str(self)


class Deck:
    size: int
    cards: List[Card]

    def __init__(self, size: int):
        self.size = size
        self.cards = []
        self.init_deck()

    def init_deck(self):
        for i in range(self.size):
            self.cards.append(Card(i))
        return

    def __str__(self):
        card_order = ','.join([str(c.pos) for c in self.cards])
        s = f"Deck({self.size})[{card_order}]"
        return s

    def shuffle(self, order_maps: List[int]):
        assert len(order_maps) == len(self.cards) == len(set(order_maps))
        new_cards = [self.cards[i] for i in order_maps]
        self.cards.clear()
        for c in new_cards:
            self.cards.append(c)

    def split(self, pos_list: List[List[int]]):
        split_decks = []
        for positions in pos_list:
            d = Deck(len(positions))
            d.cards.clear()
            for p in positions:
                d.cards.append(self.cards[p])
            split_decks.append(d)
        return split_decks

    @classmethod
    def merge(cls, decks: List['Deck']):
        d = Deck(sum([len(d) for d in decks]))
        d.cards.clear()
        for d_ in decks:
            for c in d_.cards:
                d.cards.append(c)
        return d

    def __len__(self) -> int:
        return len(self.cards)

    def __repr__(self):
        return str(self)


class Shuffler:
    def __init__(self, seed: int = 0):
        self.random = Random(seed)
        self.seed = seed

    def deal(self, deck: Deck, pile_divisions: List[int]):
        def deal_step(d: Deck, div: int):
            piles = [[] for _ in range(div)]
            p = 0
            for i, c in enumerate(d.cards):
                piles[p].append(i)
                p += 1
                p %= div
            division_idx = list(range(div))
            pile_stack = self.random.sample(division_idx, div)
            stack = []
            for p_i in pile_stack:
                stack.extend(piles[p_i])
            d.shuffle(stack)

        for division in pile_divisions:
            deal_step(deck, division)

    def hindu(self, deck: Deck, steps: List[int], divining_error: float = 0.0):

        assert 0.0 <= divining_error < 1.0

        def hindu_step(d: Deck, step: int, error: float):
            divine_errors = [2.0 * error * (self.random.random() - 0.5) for _ in range(step)]
            ideal_pile_size = len(d) / (step + 1)
            pile_sizes = []
            current_pile_size_total = 0
            for i in range(step):
                pile_size = ideal_pile_size * (1.0 + divine_errors[i])

                if current_pile_size_total + pile_size > float(len(d)):
                    pile_sizes.append(float(len(d)))
                else:
                    pile_sizes.append(current_pile_size_total + pile_size)
                current_pile_size_total += pile_size
            pile_sizes.append(float(len(d)))

            count_finished = 0
            reverse_maps = []
            for i in range(step + 1):
                int_ps = int(pile_sizes[i])
                for j in range(int_ps - count_finished):
                    reverse_maps.append(int_ps - 1 - j)
                count_finished = int_ps
            d.shuffle(reverse_maps[::-1])

        for s in steps:
            hindu_step(deck, s, divining_error)

    def over_hand(self, deck: Deck, steps: List[int], divining_error: float = 0.0):
        self.hindu(deck, steps, divining_error)

    def fallow(self, deck: Deck, iterations: int, split_error: float = 0.0, mix_error: float = 0.0):

        assert 0.0 <= split_error < 1.0
        assert 0.0 <= mix_error < 1.0

        def fallow_iteration(d: Deck, serror: float, merror: float):
            ideal_split = len(d) / float(2)
            serror = 2.0 * serror * (self.random.random() - 0.5)
            split = int(ideal_split * (1.0 + serror))

            piles = [[j for j in range(0, split)],
                     [j for j in range(split, len(d))]]
            pile_sizes = [len(piles[0]), len(piles[1])]

            if pile_sizes[0] < pile_sizes[1]:
                pile_sizes = [len(piles[1]), len(piles[0])]
                piles = [piles[1], piles[0]]

            mix_pos_rate = self.random.random()
            mix_pos_candidate = pile_sizes[0] - pile_sizes[1]
            mix_pos = int(mix_pos_candidate * mix_pos_rate)

            order = []

            for p in range(mix_pos):
                order.append(piles[0][p])
            piles[0] = piles[0][mix_pos:]
            pile_sizes[0] = len(piles[0])

            mixed_sizes = [0, 0]

            def decide_mix_batch(error: float, stop: int):
                batch_size = 1
                while batch_size < stop:
                    if self.random.random() <= error:
                        batch_size += 1
                    else:
                        break
                return batch_size

            while (mixed_sizes[0] < pile_sizes[0]) and (mixed_sizes[1] < pile_sizes[1]):
                batch_size1 = decide_mix_batch(merror, pile_sizes[1] - mixed_sizes[1])
                batch_size0 = decide_mix_batch(merror, pile_sizes[0] - mixed_sizes[0])
                for b in range(batch_size1):
                    order.append(piles[1][mixed_sizes[1]])
                    mixed_sizes[1] += 1
                for b in range(batch_size0):
                    order.append(piles[0][mixed_sizes[0]])
                    mixed_sizes[0] += 1

            if mixed_sizes[0] < pile_sizes[0]:
                for p in range(mixed_sizes[0], pile_sizes[0]):
                    order.append(piles[0][p])

            if mixed_sizes[1] < pile_sizes[1]:
                for p in range(mixed_sizes[1], pile_sizes[1]):
                    order.append(piles[1][p])

            d.shuffle(order)

        for i in range(iterations):
            fallow_iteration(deck, split_error, mix_error)

    def cut(self, deck: Deck, split: int, split_error: float = 0.0):
        assert 0.0 <= split_error < 1.0
        divine_errors = [2.0 * split_error * (self.random.random() - 0.5) for _ in range(split)]
        ideal_pile_size = len(deck) / (split + 1)
        pile_sizes = [0]
        current_pile_size_total = 0
        for i in range(split):
            pile_size = ideal_pile_size * (1.0 + divine_errors[i])

            if current_pile_size_total + pile_size > float(len(deck)):
                pile_sizes.append(float(len(deck)))
            else:
                pile_sizes.append(current_pile_size_total + pile_size)
            current_pile_size_total += pile_size
        pile_sizes.append(float(len(deck)))
        piles = [list(range(int(pile_sizes[i]), int(pile_sizes[i + 1]))) for i in range(split + 1)]
        order = []
        for i in range(split + 1):
            pile = piles[split - i]
            order.extend(pile)
        deck.shuffle(order)

    def split(self, deck: Deck, n_piles: int, split_error: float = 0.0):
        split = n_piles - 1
        assert 0.0 <= split_error < 1.0
        divine_errors = [2.0 * split_error * (self.random.random() - 0.5) for _ in range(split)]
        ideal_pile_size = len(deck) / (split + 1)
        pile_sizes = [0]
        current_pile_size_total = 0
        for i in range(split):
            pile_size = ideal_pile_size * (1.0 + divine_errors[i])

            if current_pile_size_total + pile_size > float(len(deck)):
                pile_sizes.append(float(len(deck)))
            else:
                pile_sizes.append(current_pile_size_total + pile_size)
            current_pile_size_total += pile_size
        pile_sizes.append(float(len(deck)))
        piles = [list(range(int(pile_sizes[i]), int(pile_sizes[i + 1]))) for i in range(split + 1)]
        return deck.split(piles)

    def merge(self, decks: List[Deck]):
        return Deck.merge(decks)

    def super_deal(self, decks: List[Deck], pile_divisions: List[int]):
        for d in decks:
            self.deal(d, pile_divisions)

    def super_hindu(self, decks: List[Deck], steps: List[int], divining_error: float = 0.0):
        for d in decks:
            self.hindu(d, steps, divining_error)

    def super_over_hand(self, decks: List[Deck], steps: List[int], divining_error: float = 0.0):
        self.super_hindu(decks, steps, divining_error)

    def super_fallow(self, decks: List[Deck], iterations: int, split_error: float = 0.0, mix_error: float = 0.0):
        for d in decks:
            self.fallow(d, iterations, split_error, mix_error)

    def super_cut(self, decks: List[Deck], split: int, split_error: float = 0.0):
        for d in decks:
            self.cut(d, split, split_error)

    def super_split(self, decks: List[Deck], n_piles: int, split_error: float = 0.0):
        split_decks = []
        for d in decks:
            decks = self.split(d, n_piles, split_error)
            split_decks.extend(decks)
        return split_decks


def evaluate(shuffle, deck_size: int, n: int = 10000):
    pos_counter = [[0 for j in range(deck_size)] for i in range(deck_size)]
    neighbor_counter = [[0 for j in range(deck_size)] for i in range(deck_size)]

    for i in tqdm(range(n)):
        d = Deck(deck_size)
        shuffler = Shuffler(seed=i)
        shuffled_d = shuffle(d, shuffler)

        for j in range(deck_size):
            org_pos = shuffled_d.cards[j].pos
            pos_counter[org_pos][j] += 1

            if j + 1 >= deck_size:
                continue
            next_card_org_pos = shuffled_d.cards[j + 1].pos
            neighbor_counter[org_pos][next_card_org_pos] += 1
    pos_prob_array = numpy.array(pos_counter) / float(n)
    neighbor_prob_array = numpy.array(neighbor_counter) / float(n)
    pos_prob_badness = numpy.abs(pos_prob_array - (1.0 / deck_size))
    neighbor_prob_badness = numpy.abs(neighbor_prob_array - (1.0 / (deck_size - 1)))
    for i in range(deck_size):
        neighbor_prob_badness[i, i] = 0

    nb = neighbor_prob_badness
    nb_flat = nb.flatten()
    idx = nb_flat.argsort()[-60:]
    total_nb = nb_flat[idx].mean() / (1 / deck_size)

    pb = pos_prob_badness
    pb_flat = pb.flatten()
    idx = pb_flat.argsort()[-60:]
    total_pb = pb_flat[idx].mean() / (1 / deck_size)

    return pos_prob_array, neighbor_prob_array, pos_prob_badness, neighbor_prob_badness, total_pb, total_nb
